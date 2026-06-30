import math
import sys

import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from geometry_msgs.msg import TwistStamped
from sensor_msgs.msg import Joy, JoyFeedback, LaserScan

MAX_LIN = 0.22
MAX_ANG = 2.84
MOVE_EPS = 0.03
LIN_EPS = 0.01

# Soft low-frequency motor ONLY (the high-freq motor is harsh / hurts hands).
DRIVE_BASE, DRIVE_GAIN = 0.08, 0.08   # moving: ~0.08 .. 0.16
DRIVE_CAP = 0.16

# Proximity warning from the lidar: ramps up as you drive toward an obstacle.
CONE_HALF = math.radians(50)          # front/rear arc half-width
WARN_DIST = 0.8                       # start warning below this (m)
CRIT_DIST = 0.20                      # full warning at/below this (m)
PROX_MIN, PROX_MAX = 0.18, 0.70
SCAN_STALE = 1.0

SMOOTH_HZ = 30.0
ALPHA_UP = 0.20
ALPHA_DOWN = 0.45
SEND_EPS = 0.015
REFRESH_SEC = 0.6
STALE_SEC = 0.5

LT_AXIS, RT_AXIS = 4, 5
TRIG_RELEASED = 1.0
BRAKE_ON = 0.0


class TeleopBrakeRumble(Node):
    def __init__(self):
        super().__init__('teleop_brake_rumble')
        self.twist_in = None
        self.last_twist = self.get_clock().now()
        self.axes = []
        self.tick_n = 0
        self.level = 0.0
        self.last_sent = -1.0
        self.last_send_t = self.get_clock().now()
        self.front_dist = float('inf')
        self.rear_dist = float('inf')
        self.last_scan = self.get_clock().now()
        self.proximity_on = self.declare_parameter('proximity_warning', False).value
        self.create_subscription(TwistStamped, '/cmd_vel_teleop', self.on_twist, 10)
        self.create_subscription(Joy, '/joy', self.on_joy, 10)
        if self.proximity_on:
            self.create_subscription(LaserScan, '/scan', self.on_scan, qos_profile_sensor_data)
        self.cmd_pub = self.create_publisher(TwistStamped, '/cmd_vel', 10)
        self.fb_pub = self.create_publisher(JoyFeedback, '/joy/set_feedback', 10)
        self.create_timer(1.0 / SMOOTH_HZ, self.rumble_tick)
        self._set_motor(1, 0.0)
        extra = 'lidar proximity ON' if self.proximity_on else 'lidar proximity off'
        self.get_logger().info(f'teleop_brake_rumble: drive hum + LT/RT brake ({extra})')

    def braking(self):
        a = self.axes
        lt = a[LT_AXIS] if len(a) > LT_AXIS else TRIG_RELEASED
        rt = a[RT_AXIS] if len(a) > RT_AXIS else TRIG_RELEASED
        return lt < BRAKE_ON or rt < BRAKE_ON

    def publish_cmd(self):
        out = TwistStamped()
        out.header.stamp = self.get_clock().now().to_msg()
        if not self.braking() and self.twist_in is not None:
            out.twist = self.twist_in.twist
        self.cmd_pub.publish(out)

    def on_twist(self, msg):
        self.twist_in = msg
        self.last_twist = self.get_clock().now()
        self.publish_cmd()

    def on_joy(self, msg):
        was = self.braking()
        self.axes = list(msg.axes)
        if self.braking() != was:
            self.publish_cmd()

    def on_scan(self, msg):
        self.last_scan = self.get_clock().now()
        front = float('inf')
        rear = float('inf')
        ang = msg.angle_min
        for r in msg.ranges:
            if msg.range_min <= r <= msg.range_max:
                a = math.atan2(math.sin(ang), math.cos(ang))
                if abs(a) <= CONE_HALF:
                    front = min(front, r)
                elif abs(abs(a) - math.pi) <= CONE_HALF:
                    rear = min(rear, r)
            ang += msg.angle_increment
        self.front_dist = front
        self.rear_dist = rear

    def _set_motor(self, mid, val):
        fb = JoyFeedback()
        fb.type = JoyFeedback.TYPE_RUMBLE
        fb.id = mid
        fb.intensity = float(max(0.0, min(val, 1.0)))
        self.fb_pub.publish(fb)

    def drive_level(self):
        lf = min(abs(self.twist_in.twist.linear.x) / MAX_LIN, 1.0)
        af = min(abs(self.twist_in.twist.angular.z) / MAX_ANG, 1.0)
        frac = min(lf + 0.5 * af, 1.0)
        if frac <= MOVE_EPS:
            return 0.0
        return min(DRIVE_BASE + DRIVE_GAIN * frac, DRIVE_CAP)

    def proximity_level(self):
        if (self.get_clock().now() - self.last_scan).nanoseconds * 1e-9 > SCAN_STALE:
            return 0.0
        v = self.twist_in.twist.linear.x
        if v > LIN_EPS:
            d = self.front_dist
        elif v < -LIN_EPS:
            d = self.rear_dist
        else:
            return 0.0
        if d >= WARN_DIST:
            return 0.0
        p = (WARN_DIST - d) / (WARN_DIST - CRIT_DIST)
        p = max(0.0, min(p, 1.0))
        return PROX_MIN + (PROX_MAX - PROX_MIN) * p

    def target_level(self):
        if self.braking():
            return 0.0
        age = (self.get_clock().now() - self.last_twist).nanoseconds * 1e-9
        if self.twist_in is None or age > STALE_SEC:
            return 0.0
        prox = self.proximity_level() if self.proximity_on else 0.0
        return max(self.drive_level(), prox)

    def rumble_tick(self):
        self.tick_n += 1
        target = self.target_level()
        a = ALPHA_UP if target > self.level else ALPHA_DOWN
        self.level += a * (target - self.level)
        if target == 0.0 and self.level < 0.02:
            self.level = 0.0
        now = self.get_clock().now()
        dt = (now - self.last_send_t).nanoseconds * 1e-9
        if abs(self.level - self.last_sent) >= SEND_EPS or dt >= REFRESH_SEC:
            self._set_motor(0, self.level)
            self.last_sent = self.level
            self.last_send_t = now


def main(args=None):
    rclpy.init(args=args if args is not None else sys.argv)
    node = TeleopBrakeRumble()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node._set_motor(0, 0.0)
        node._set_motor(1, 0.0)
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
