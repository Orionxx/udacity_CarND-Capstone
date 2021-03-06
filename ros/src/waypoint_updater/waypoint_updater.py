#!/usr/bin/env python

import rospy
from std_msgs.msg import Int32
from geometry_msgs.msg import PoseStamped
from styx_msgs.msg import Lane, Waypoint

import math

from scipy.spatial import KDTree
import numpy as np

'''
This node will publish waypoints from the car's current position to some `x` distance ahead.

As mentioned in the doc, you should ideally first implement a version which does not care
about traffic lights or obstacles.

Once you have created dbw_node, you will update this node to use the status of traffic lights too.

Please note that our simulator also provides the exact location of traffic lights and their
current status in `/vehicle/traffic_lights` message. You can use this message to build this node
as well as to verify your TL classifier.

TODO (for Yousuf and Aaron): Stopline location for each traffic light.
'''

LOOKAHEAD_WPS = 60 # Number of waypoints we will publish. You can change this number
MAX_DECEL = 2


class WaypointUpdater(object):
    def __init__(self):
        rospy.init_node('waypoint_updater')

        rospy.Subscriber('/current_pose', PoseStamped, self.pose_cb)
        rospy.Subscriber('/base_waypoints', Lane, self.waypoints_cb)

        # TODO: Add a subscriber for /traffic_waypoint and /obstacle_waypoint below
        rospy.Subscriber('/traffic_waypoint', Int32, self.traffic_cb)
        rospy.Subscriber('/obstacle_waypoint', Int32, self.obstacle_cb)

        self.final_waypoints_pub = rospy.Publisher('/final_waypoints', Lane, queue_size=1)

        # TODO: Add other member variables you need below
        self.pose = None
        self.waypoints = None
        self.tree = None
        self.stopline = -1
        
        #rospy.spin()
        self.loop()
        
    def loop(self):
        rate = rospy.Rate(5) # 5Hz
        while not rospy.is_shutdown():
            if self.tree and self.pose:
                id = self.calcID()
                self.publish(id)
            rate.sleep()
            
    def publish(self, id):
        lane = Lane()
        lane.header = self.waypoints.header
        waypoints = self.waypoints.waypoints[id:id + LOOKAHEAD_WPS]
        #rospy.logerr('Stopline bekommen: {}, bei id: {}'.format(self.stopline, id))
        if self.stopline < id or self.stopline > id + LOOKAHEAD_WPS:
          lane.waypoints = waypoints
          rospy.loginfo('Fahren')
        else:
          lane.waypoints = self.brake(waypoints, id)
          rospy.loginfo('Bremsen')
        self.final_waypoints_pub.publish(lane)
        
    def brake(self, waypoints, id):
      ret = []
      
      stop = max(self.stopline - id - 4, 0)
      for i, wp in enumerate(waypoints):
        p = Waypoint()
        p.pose = wp.pose
        
        dist = self.distance(waypoints, i, stop)
        vel = math.sqrt(2 * MAX_DECEL * dist)
        if vel < 1.:
          vel = 0
         
        self.set_waypoint_velocity(p, min(vel, self.get_waypoint_velocity(wp)))
        ret.append(p)
        
      return ret
    
    def calcID(self):
        x, y = self.pose.pose.position.x, self.pose.pose.position.y
        
        id = self.tree.query([x, y])[1]
        
        p0 = np.array(self.waypoints_2d[id])
        p1 = np.array(self.waypoints_2d[id - 1])
        
        if np.dot(p0 - p1, np.array([x, y]) - p0) > 0:
            return (id + 1) % len(self.waypoints_2d)
        else:
            return id

    def pose_cb(self, msg):
        # TODO: Implement
        self.pose = msg

    def waypoints_cb(self, waypoints):
        # TODO: Implement
        self.waypoints = waypoints
        self.waypoints_2d = [[p.pose.pose.position.x, p.pose.pose.position.y] for p in waypoints.waypoints]
        self.tree = KDTree(self.waypoints_2d)

    def traffic_cb(self, msg):
        # TODO: Callback for /traffic_waypoint message. Implement
        self.stopline = msg.data

    def obstacle_cb(self, msg):
        # TODO: Callback for /obstacle_waypoint message. We will implement it later
        pass

    def get_waypoint_velocity(self, waypoint):
        return waypoint.twist.twist.linear.x

    def set_waypoint_velocity(self, waypoint, velocity):
        waypoint.twist.twist.linear.x = velocity

    def distance(self, waypoints, wp1, wp2):
        dist = 0
        dl = lambda a, b: math.sqrt((a.x-b.x)**2 + (a.y-b.y)**2  + (a.z-b.z)**2)
        for i in range(wp1, wp2+1):
            dist += dl(waypoints[wp1].pose.pose.position, waypoints[i].pose.pose.position)
            wp1 = i
        return dist


if __name__ == '__main__':
    try:
        WaypointUpdater()
    except rospy.ROSInterruptException:
        rospy.logerr('Could not start waypoint updater node.')
