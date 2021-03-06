import glob
import os
import sys
import time
import random
import math
import numpy as np
import cv2
from queue import Queue
from queue import Empty
from gym import spaces
import gym


try:
    sys.path.append(glob.glob('../carla/dist/carla-*%d.%d-%s.egg' % (
        sys.version_info.major,
        sys.version_info.minor,
        'win-amd64' if os.name == 'nt' else 'linux-x86_64'))[0])
except IndexError:
    pass
import carla

IM_WIDTH = 400
IM_HEIGHT = 400
IM_FOV = 110
MAX_SENSOR_DISTANCE = 40

SHOW_PREVIEW = True
class ENV(gym.Env):
    metadata = {"render.modes": ["human"]}
    def __init__(self):
        super(ENV, self).__init__()
        self.client = carla.Client("localhost", 2000)

        self.client.set_timeout(8.0)
        # self.world = self.client.load_world('Town01')
        self.world = self.client.get_world()
        self.blueprint_library = self.world.get_blueprint_library()
        self.autopilot_bp = self.blueprint_library.filter("model3")[0]
        self.map = self.world.get_map()
        self.actor_list = []
        self.sensor_list = {}
        self.action_space = spaces.MultiDiscrete([3, 3])
        self.observation_space = spaces.Box(0,1,shape=(9,),dtype =np.float32)
        # self.observation_space_shape = (10,)
        self.custom_spawn_points = [[-40, 165, 90], [-40,170,0], [-40,165,0], [-40,170,90], [-40,175,0], [-40,175,90],
                                    [-40,180,0], [-40,180,90], [-40,185,0], [-40,185,90], [-40,190,0], [-40,190,90],
                                    [-40,180,180],[-40,192,0],[-40,192,90],[-40,192,180],[-45,192,0],[-45,192,90],
                                    [-45,192,180], [-50,192,0],[-50,192,90],[-50,192,180],[-55,192,0],[-55,192,90],
                                    [-55,192,180],[-60,192,0],[-60,192,90],[-60,192,180],[-65,192,180],[-65,192,0]]


    def set_sensor_obstacle(self, x_position,y_position, orientation):
        sensor_blueprint = self.blueprint_library.find("sensor.other.obstacle")
        sensor_options = {"distance": f"{MAX_SENSOR_DISTANCE}", "debug_linetrace": "True", "hit_radius": "0.1"}
        for key in sensor_options:
            sensor_blueprint.set_attribute(key, sensor_options[key])
        sensor_spawn_point = carla.Transform(carla.Location(x = x_position, y = y_position, z = 0.3),
                                             carla.Rotation(yaw = orientation))
        sensor = self.world.spawn_actor(sensor_blueprint, sensor_spawn_point,
                                        attach_to = self.autopilot_vehicle,
                                        attachment_type = carla.AttachmentType.Rigid)
        # self.sensor_list[f"obstacle_{number}"] = self.world.spawn_actor(sensor_blueprint, sensor_spawn_point,
        #                                                                 attach_to = self.autopilot_vehicle,
        #                                                                 attachment_type = carla.AttachmentType.Rigid)
        # self.actor_list.append(self.sensor_list[f"obstacle_{number}"])
        self.actor_list.append(sensor)
        return sensor

    def sensor_callback(self,data,queue):
        queue.put(data)

    def set_sensor_camera(self):
        camera_blueprint = self.blueprint_library.find("sensor.camera.rgb")
        self.camera_blueprint = camera_blueprint
        camera_blueprint.set_attribute("image_size_x", f"{IM_WIDTH}")
        camera_blueprint.set_attribute("image_size_y", f"{IM_HEIGHT}")
        camera_blueprint.set_attribute("fov", f"{IM_FOV}")
        cam_spawn_point = carla.Transform(carla.Location(x=-4, z= 3), carla.Rotation(yaw=0.0, pitch = -20.0))
        self.camera_sensor = self.world.spawn_actor(camera_blueprint, cam_spawn_point, attach_to=self.autopilot_vehicle,
                                                    attachment_type=carla.AttachmentType.Rigid)
        self.actor_list.append(self.camera_sensor)

    def process_camera_image(self,image_data):

        im_array = np.copy(np.frombuffer(image_data.raw_data, dtype=np.dtype("int8")))
        im_array = np.reshape(im_array, (IM_HEIGHT, IM_WIDTH, 4))
        im_array2 = im_array[:, :, :3]
        return im_array2

    def process_obstacle_data(self, obstacle_data_list):
        distances_data = []
        for obstacle in obstacle_data_list:
            distances_data.append(obstacle.distance)
        return distances_data

    def calculate_distance(self):
        goal_point = [-67.8, 177.8]
        vehicle_location = [self.autopilot_vehicle.get_location().x, self.autopilot_vehicle.get_location().y]
        distance = math.sqrt((goal_point[0] - vehicle_location[0])**2 + (goal_point[1] - vehicle_location[1])**2)
        if distance > MAX_SENSOR_DISTANCE:
            distance = MAX_SENSOR_DISTANCE
        return distance



    def execute_action(self, action):
        #2 actions, first is Gas, nothing, reverse. Second is left, right or nothing
        if action[0] == 0:
            throttle = 0
            reverse = False
        elif action[0] == 1:
            throttle = 1
            reverse = False
        elif action[0] == 2:
            throttle = 1
            reverse = True
        if action[1] == 0:
            steer = 0
        elif action[1] == 1:
            steer = 1
        elif action[1] == 2:
            steer = -1

        self.autopilot_vehicle.apply_control(carla.VehicleControl(throttle=throttle, brake=0,
                                                                  steer=steer, reverse = reverse))
    def reset(self):
        self.queue_dict = {}
        spawn_point_coords = random.choice(self.custom_spawn_points)
        # self.spawn_point = random.choice(self.map.get_spawn_points())
        self.spawn_point = carla.Transform(carla.Location(x=spawn_point_coords[0], y=spawn_point_coords[1], z=0.600000),
                                           carla.Rotation(pitch=0.000000, yaw=spawn_point_coords[2], roll=0.000000))
        # DEFINIRATI x = -40, y = 165, yaw = 90
        #GOAL POINT x = -67.8, y = 177.8
        self.autopilot_vehicle = self.world.spawn_actor(self.autopilot_bp,self.spawn_point)
        self.actor_list.append(self.autopilot_vehicle)
        time.sleep(0.5)
        obstacle_sensor_positions = [[2.7, 0, 0],#front
                                     [2.5, -0.6, -45],#front left
                                     [2.5, 0.6, 45], #front right
                                     [-2.3, 0, 180], #back
                                     [-2.3, -0.6, -135], #back left
                                     [-2.3, 0.6, 135], #back right
                                     [0, -0.5, -90], #left
                                     [0, 0.5, 90]] #right

        self.front_sensor = self.set_sensor_obstacle(obstacle_sensor_positions[0][0],
                                                     obstacle_sensor_positions[0][1],
                                                     obstacle_sensor_positions[0][2])
        self.front_left_sensor = self.set_sensor_obstacle(obstacle_sensor_positions[1][0],
                                                     obstacle_sensor_positions[1][1],
                                                     obstacle_sensor_positions[1][2])
        self.front_right_sensor = self.set_sensor_obstacle(obstacle_sensor_positions[2][0],
                                                     obstacle_sensor_positions[2][1],
                                                     obstacle_sensor_positions[2][2])
        self.back_sensor = self.set_sensor_obstacle(obstacle_sensor_positions[3][0],
                                                     obstacle_sensor_positions[3][1],
                                                     obstacle_sensor_positions[3][2])
        self.back_left_sensor = self.set_sensor_obstacle(obstacle_sensor_positions[4][0],
                                                     obstacle_sensor_positions[4][1],
                                                     obstacle_sensor_positions[4][2])
        self.back_right_sensor = self.set_sensor_obstacle(obstacle_sensor_positions[5][0],
                                                     obstacle_sensor_positions[5][1],
                                                     obstacle_sensor_positions[5][2])
        self.left_sensor = self.set_sensor_obstacle(obstacle_sensor_positions[6][0],
                                                     obstacle_sensor_positions[6][1],
                                                     obstacle_sensor_positions[6][2])
        self.right_sensor = self.set_sensor_obstacle(obstacle_sensor_positions[7][0],
                                                    obstacle_sensor_positions[7][1],
                                                    obstacle_sensor_positions[7][2])
        self.front_sensor_queue = Queue(maxsize=1)
        self.front_right_sensor_queue = Queue(maxsize=1)
        self.front_left_sensor_queue = Queue(maxsize=1)
        self.back_sensor_queue = Queue(maxsize=1)
        self.back_left_sensor_queue = Queue(maxsize=1)
        self.back_right_sensor_queue = Queue(maxsize=1)
        self.left_sensor_queue = Queue(maxsize=1)
        self.right_sensor_queue = Queue(maxsize=1)

        self.front_sensor.listen((lambda data: self.sensor_callback(data, self.front_sensor_queue)))
        self.front_left_sensor.listen((lambda data: self.sensor_callback(data, self.front_left_sensor_queue)))
        self.front_right_sensor.listen((lambda data: self.sensor_callback(data, self.front_right_sensor_queue)))
        self.back_sensor.listen((lambda data: self.sensor_callback(data, self.back_sensor_queue)))
        self.back_left_sensor.listen((lambda data: self.sensor_callback(data, self.back_left_sensor_queue)))
        self.back_right_sensor.listen((lambda data: self.sensor_callback(data, self.back_right_sensor_queue)))
        self.left_sensor.listen((lambda data: self.sensor_callback(data, self.left_sensor_queue)))
        self.right_sensor.listen((lambda data: self.sensor_callback(data, self.right_sensor_queue)))

        # for number, points in enumerate(obstacle_sensor_positions):
        #     self.set_sensor_obstacle(number, points[0], points[1], points[2])
        #     self.queue_dict[f"obstacle_queue_{number}"] = Queue(maxsize=1)
        # for sensor, queue in zip(self.sensor_list.keys(), self.queue_dict.keys()):
        #     self.sensor_list[sensor].listen(lambda data: self.sensor_callback(data, self.queue_dict[queue]))
        self.set_sensor_camera()
        self.camera_queue = Queue(maxsize=1)
        self.camera_sensor.listen(lambda data: self.sensor_callback(data, self.camera_queue))
        # self.autopilot_vehicle.apply_control(carla.VehicleControl(throttle = 0.3, steer = 0.1))
        self.world.tick()

    def step(self, action):
        obstacle_data = []
        if not self.front_sensor_queue.empty():
            front_sensor = self.front_sensor_queue.get(True,1.0)
            front_sensor = front_sensor.distance
            obstacle_data.append(front_sensor)
        else:
            front_sensor = MAX_SENSOR_DISTANCE
            obstacle_data.append(front_sensor)
        if not self.front_left_sensor_queue.empty():
            front_left_sensor = self.front_left_sensor_queue.get(True,1.0)
            front_left_sensor = front_left_sensor.distance
            obstacle_data.append(front_left_sensor)
        else:
            front_left_sensor = MAX_SENSOR_DISTANCE
            obstacle_data.append(front_left_sensor)
        if not self.front_right_sensor_queue.empty():
            front_right_sensor = self.front_right_sensor_queue.get(True,1.0)
            front_right_sensor = front_right_sensor.distance
            obstacle_data.append(front_right_sensor)
        else:
            front_right_sensor = MAX_SENSOR_DISTANCE
            obstacle_data.append(front_right_sensor)
        if not self.back_sensor_queue.empty():
            back_sensor = self.back_sensor_queue.get(True,1.0)
            back_sensor = back_sensor.distance
            obstacle_data.append(back_sensor)
        else:
            back_sensor = MAX_SENSOR_DISTANCE
            obstacle_data.append(back_sensor)
        if not self.back_left_sensor_queue.empty():
            back_left_sensor = self.back_left_sensor_queue.get(True,1.0)
            back_left_sensor = back_left_sensor.distance
            obstacle_data.append(back_left_sensor)
        else:
            back_left_sensor = MAX_SENSOR_DISTANCE
            obstacle_data.append(back_left_sensor)
        if not self.back_right_sensor_queue.empty():
            back_right_sensor = self.back_right_sensor_queue.get(True,1.0)
            back_right_sensor = back_right_sensor.distance
            obstacle_data.append(back_right_sensor)
        else:
            back_right_sensor = MAX_SENSOR_DISTANCE
            obstacle_data.append(back_right_sensor)
        if not self.left_sensor_queue.empty():
            left_sensor = self.left_sensor_queue.get(True,1.0)
            left_sensor = left_sensor.distance
            obstacle_data.append(left_sensor)
        else:
            left_sensor = MAX_SENSOR_DISTANCE
            obstacle_data.append(left_sensor)
        if not self.right_sensor_queue.empty():
            right_sensor = self.right_sensor_queue.get(True,1.0)
            right_sensor = right_sensor.distance
            obstacle_data.append(right_sensor)
        else:
            right_sensor = MAX_SENSOR_DISTANCE
            obstacle_data.append(right_sensor)

        try:
            camera_data = self.camera_queue.get(True,1.0)
        except Empty:
            with self.camera_queue.mutex:
                self.camera_queue.queue.clear()
                print("CAMERA SENSOR MISSING")
        distance = self.calculate_distance()
        obstacle_data.append(distance)
        reward = (50-distance)/5
        camera_image = self.process_camera_image(camera_data)

        img_rgb = cv2.cvtColor(camera_image.astype("uint8"), cv2.COLOR_BGR2RGB)

        cv2.imshow("1", img_rgb)
        cv2.waitKey(1)
        self.execute_action(action)
        obstacle_data = np.array(obstacle_data,dtype="int8")/40
        print(obstacle_data.shape)
        return obstacle_data, reward

if __name__ == "__main__":
    try:
        env = ENV()
        settings = env.world.get_settings()
        original_settings = env.world.get_settings()
        settings.synchronous_mode = True  # Enables synchronous mode
        settings.fixed_delta_seconds = 0.1  # 1 frame = 0.1 second
        env.world.apply_settings(settings)
        env.reset()
        for _ in range(10000):
            start_time = time.time()
            data = env.step(action=[0, 0])
            env.world.tick()
            time.sleep(0.07)
            print(data)
            # print("FPS: ", 1.0 / (time.time() - start_time))

    except KeyboardInterrupt:
        env.client.apply_batch([carla.command.DestroyActor(x) for x in env.actor_list])
        print("Actors destroyed")
        time.sleep(1)
    finally:
        # try:
        #     self.world.apply_settings(original_settings)
        # except NameError:
        #     pass

        env.client.apply_batch([carla.command.DestroyActor(x) for x in env.actor_list])

        time.sleep(3)
