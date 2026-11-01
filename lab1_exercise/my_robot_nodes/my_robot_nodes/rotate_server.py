import math
import time

import rclpy
from geometry_msgs.msg import Twist
from nav_msgs.msg import Odometry
from rclpy.action import ActionServer, CancelResponse, GoalResponse
from rclpy.callback_groups import ReentrantCallbackGroup
from rclpy.executors import ExternalShutdownException, MultiThreadedExecutor
from rclpy.node import Node

from my_robot_interfaces.action import Rotate


def yaw_from_quaternion(q):
    """Rotation about the vertical axis, in rad, of an orientation quaternion."""
    return math.atan2(2.0 * (q.w * q.z + q.x * q.y), 1.0 - 2.0 * (q.y * q.y + q.z * q.z))


def angle_difference(target, current):
    """target - current, wrapped to [-pi, pi]."""
    return math.atan2(math.sin(target - current), math.cos(target - current))


class RotateServer(Node):

    def __init__(self):
        super().__init__("rotate_server")
        self.declare_parameter("turn_speed", 0.5)

        self.yaw = None

        # The goal runs in a loop, so the odometry callback needs its own thread
        group = ReentrantCallbackGroup()
        self.cmd_vel = self.create_publisher(Twist, "cmd_vel", 10)
        self.create_subscription(Odometry, "odom", self.on_odom, 10, callback_group=group)
        self.action_server = ActionServer(
            self, Rotate, "rotate",
            execute_callback=self.execute,
            goal_callback=self.on_goal,
            cancel_callback=lambda goal_handle: CancelResponse.ACCEPT,
            callback_group=group,
        )

    def on_odom(self, msg):
        self.yaw = yaw_from_quaternion(msg.pose.pose.orientation)

    def on_goal(self, goal):
        # A goal of zero is rejected, and so is any goal before the first odometry arrives
        if goal.angle == 0.0 or self.yaw is None:
            return GoalResponse.REJECT
        return GoalResponse.ACCEPT

    def execute(self, goal_handle):
        goal = goal_handle.request.angle
        direction = 1.0 if goal > 0.0 else -1.0
        self.get_logger().info(f"Turning {goal:.2f} rad")

        twist = Twist()
        twist.angular.z = direction * self.get_parameter("turn_speed").value
        feedback = Rotate.Feedback()
        result = Rotate.Result()

        # Add up the small yaw changes, so the jump from pi to -pi does not matter
        last_yaw = self.yaw
        turned = 0.0

        while rclpy.ok():
            yaw = self.yaw
            turned += angle_difference(yaw, last_yaw)
            last_yaw = yaw
            result.turned = float(turned)

            if goal_handle.is_cancel_requested:
                self.cmd_vel.publish(Twist())
                goal_handle.canceled()
                self.get_logger().info(f"Canceled after {turned:.2f} rad")
                return result
            if abs(turned) >= abs(goal):
                break

            self.cmd_vel.publish(twist)
            feedback.turned = float(turned)
            goal_handle.publish_feedback(feedback)
            time.sleep(0.1)

        self.cmd_vel.publish(Twist())
        goal_handle.succeed()
        self.get_logger().info(f"Turned {turned:.2f} rad")
        return result


def main():
    rclpy.init()
    node = RotateServer()
    try:
        rclpy.spin(node, executor=MultiThreadedExecutor())
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    node.destroy_node()
    rclpy.try_shutdown()


if __name__ == "__main__":
    main()
