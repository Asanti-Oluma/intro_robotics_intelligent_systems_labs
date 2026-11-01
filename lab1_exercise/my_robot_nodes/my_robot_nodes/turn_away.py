import rclpy
from geometry_msgs.msg import Twist
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node

from lab_interfaces.msg import ObstacleInfo
from my_robot_interfaces.msg import RobotStatus


class TurnAway(Node):

    def __init__(self):
        super().__init__("turn_away")
        self.declare_parameter("forward_speed", 0.2)
        self.declare_parameter("turn_speed", 0.5)

        self.cmd_vel = self.create_publisher(Twist, "cmd_vel", 10)
        self.status_pub = self.create_publisher(RobotStatus, "robot_status", 10)
        self.create_subscription(ObstacleInfo, "obstacle", self.on_obstacle, 10)

    def on_obstacle(self, msg):
        # Read the parameters every time, so a change takes effect at once
        forward_speed = self.get_parameter("forward_speed").value
        turn_speed = self.get_parameter("turn_speed").value

        cmd = Twist()
        if msg.too_close:
            # angle > 0 means the obstacle is on the left, so turn right
            cmd.angular.z = -turn_speed if msg.angle > 0 else turn_speed
        else:
            cmd.linear.x = forward_speed
        self.cmd_vel.publish(cmd)

        status = RobotStatus()
        status.state = "turning" if msg.too_close else "forward"
        status.obstacle_distance = msg.distance
        self.status_pub.publish(status)


def main():
    rclpy.init()
    node = TurnAway()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    node.destroy_node()
    rclpy.try_shutdown()


if __name__ == "__main__":
    main()
