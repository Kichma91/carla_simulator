import glob
import os
import sys
import time
import random
import numpy as np
import cv2
import math
from queue import Queue
from queue import Empty
from gym import spaces
from matplotlib import cm
from PIL import Image

try:
    sys.path.append(glob.glob('../carla/dist/carla-*%d.%d-%s.egg' % (
        sys.version_info.major,
        sys.version_info.minor,
        'win-amd64' if os.name == 'nt' else 'linux-x86_64'))[0])
except IndexError:
    pass
import carla

# constants for sensors
SHOW_PREVIEW = True#boolean if we want camera image to show or not
# CAMERA CONSTANTS
IM_WIDTH = 480#120#240#480#640
IM_HEIGHT = 480#90#180#360#480
IM_FOV = 110

LIDAR_RANGE = 100

#WORLD AND LEARN CONSTANTS
NPC_NUMBER = 0
JUNCTION_NUMBER = 2
FRAMES = 300
RUNS = 100
SECONDS_PER_EPISODE = 10


try:
    client = carla.Client("localhost", 2000)
    print(client.get_available_maps())
    # world = client.load_world('Town0')
except IndexError:
    pass

class ENV:
    SHOW_CAM = SHOW_PREVIEW
    STEER_AMT = 1.0
    im_width = IM_WIDTH
    im_height = IM_HEIGHT
    im_fov = IM_FOV
    def __init__(self, actions=1, action_type="C"):
        self.client = carla.Client("localhost", 2000)
        self.client.set_timeout(8.0)
        self.world = self.client.get_world()
        self.blueprint_library = self.world.get_blueprint_library()
        self.autopilot_bp = self.blueprint_library.filter("model3")[0]
        self.map = self.world.get_map()
        self.actor_list = []
        #self.observation_space_shape = (4803,)
        self.action_type = action_type
        self.action_space_size = actions
        if action_type == "C":
            if actions == 1:
                self.action_space = spaces.Box(low=np.array([-1.0]), high=np.array([1.0]), dtype=np.float32)
            elif actions == 2:
                self.action_space = spaces.Box(low=np.array([-1.0, -1.0]), high=np.array([1.0, 1.0]), dtype=np.float32)
            elif actions == 3:
                self.action_space = spaces.Box(low=np.array([-1.0, 0.0, 0, 0]), high=np.array([1.0, 1.0, 1.0]),
                                               dtype=np.float32)
        elif action_type == "D":
            self.action_space = spaces.MultiDiscrete([3, 2, 2])
        #self.observation_space_shape = ###

    def set_sensor_lidar(self):
        lidar_blueprint = self.blueprint_library.find("sensor.lidar.ray_cast")
        sensor_options = {'channels': '128', 'points_per_second': '100000', 'rotation_frequency': '20', 'upper_fov': '0',
                          'horizontal_fov': '110', }
        lidar_blueprint.set_attribute('range', f"{LIDAR_RANGE}")
        lidar_blueprint.set_attribute('dropoff_general_rate', f"{0.1}")
        lidar_blueprint.set_attribute('dropoff_intensity_limit',
                               lidar_blueprint.get_attribute('dropoff_intensity_limit').recommended_values[0])
        lidar_blueprint.set_attribute('dropoff_zero_intensity',f"{0.1}")
        for key in sensor_options:
            lidar_blueprint.set_attribute(key, sensor_options[key])
        lidar_spawn_point = carla.Transform(carla.Location(x=1.0, z=1.8), carla.Rotation(yaw=0.0))
        self.lidar_sensor = self.world.spawn_actor(lidar_blueprint, lidar_spawn_point, attach_to=self.autopilot_vehicle,
                                                   attachment_type=carla.AttachmentType.Rigid)
        self.actor_list.append(self.lidar_sensor)

    def set_sensor_back_lidar(self):
        lidar_blueprint = self.blueprint_library.find("sensor.lidar.ray_cast")
        sensor_options = {'channels': '32', 'points_per_second': '50000', 'rotation_frequency': '20',
                          'horizontal_fov': '110','upper_fov': '0'}
        lidar_blueprint.set_attribute('range', f"{LIDAR_RANGE}")
        lidar_blueprint.set_attribute('dropoff_general_rate', f"{0.1}")
        lidar_blueprint.set_attribute('dropoff_intensity_limit',
                               lidar_blueprint.get_attribute('dropoff_intensity_limit').recommended_values[0])
        lidar_blueprint.set_attribute('dropoff_zero_intensity', f"{0.1}")
        for key in sensor_options:
            lidar_blueprint.set_attribute(key, sensor_options[key])
        lidar_spawn_point = carla.Transform(carla.Location(x=-1.6, z=1.8), carla.Rotation(yaw=180.0))
        self.back_lidar_sensor = self.world.spawn_actor(lidar_blueprint, lidar_spawn_point, attach_to=self.autopilot_vehicle,
                                                   attachment_type=carla.AttachmentType.Rigid)
        self.actor_list.append(self.back_lidar_sensor)

    def set_sensor_left_lidar(self):
        lidar_blueprint = self.blueprint_library.find("sensor.lidar.ray_cast")
        sensor_options = {'channels': '32', 'points_per_second': '50000', 'rotation_frequency': '20',
                          'horizontal_fov': '110','upper_fov': '-5', 'lower_fov': '-40'}
        lidar_blueprint.set_attribute('range', f"{LIDAR_RANGE}")
        lidar_blueprint.set_attribute('dropoff_general_rate',
                               lidar_blueprint.get_attribute('dropoff_general_rate').recommended_values[0])
        lidar_blueprint.set_attribute('dropoff_intensity_limit',
                               lidar_blueprint.get_attribute('dropoff_intensity_limit').recommended_values[0])
        lidar_blueprint.set_attribute('dropoff_zero_intensity',
                               lidar_blueprint.get_attribute('dropoff_zero_intensity').recommended_values[0])
        for key in sensor_options:
            lidar_blueprint.set_attribute(key, sensor_options[key])
        lidar_spawn_point = carla.Transform(carla.Location(x=1.6, y= -0.5,  z=1.8), carla.Rotation(yaw=-100.0))
        self.left_lidar_sensor = self.world.spawn_actor(lidar_blueprint, lidar_spawn_point, attach_to=self.autopilot_vehicle,
                                                   attachment_type=carla.AttachmentType.Rigid)
        self.actor_list.append(self.left_lidar_sensor)

    def set_sensor_right_lidar(self):
        lidar_blueprint = self.blueprint_library.find("sensor.lidar.ray_cast")
        sensor_options = {'channels': '32', 'points_per_second': '50000', 'rotation_frequency': '20',
                          'horizontal_fov': '110','upper_fov': '-5', 'lower_fov': '-40'}
        lidar_blueprint.set_attribute('range', f"{LIDAR_RANGE}")
        lidar_blueprint.set_attribute('dropoff_general_rate',
                               lidar_blueprint.get_attribute('dropoff_general_rate').recommended_values[0])
        lidar_blueprint.set_attribute('dropoff_intensity_limit',
                               lidar_blueprint.get_attribute('dropoff_intensity_limit').recommended_values[0])
        lidar_blueprint.set_attribute('dropoff_zero_intensity',
                               lidar_blueprint.get_attribute('dropoff_zero_intensity').recommended_values[0])
        for key in sensor_options:
            lidar_blueprint.set_attribute(key, sensor_options[key])
        lidar_spawn_point = carla.Transform(carla.Location(x=1.6, y= 0.5,  z=1.8), carla.Rotation(yaw=100.0))
        self.right_lidar_sensor = self.world.spawn_actor(lidar_blueprint, lidar_spawn_point, attach_to=self.autopilot_vehicle,
                                                   attachment_type=carla.AttachmentType.Rigid)
        self.actor_list.append(self.right_lidar_sensor)

    def set_sensor_camera(self):
        camera_blueprint = self.blueprint_library.find("sensor.camera.semantic_segmentation")
        self.camera_blueprint = camera_blueprint
        camera_blueprint.set_attribute("image_size_x", f"{self.im_width}")
        camera_blueprint.set_attribute("image_size_y", f"{self.im_height}")
        camera_blueprint.set_attribute("fov", f"{self.im_fov}")
        cam_spawn_point = carla.Transform(carla.Location(x=1.6, z=1.6), carla.Rotation(yaw=0.0))
        self.camera_sensor = self.world.spawn_actor(camera_blueprint, cam_spawn_point, attach_to=self.autopilot_vehicle,
                                                    attachment_type=carla.AttachmentType.Rigid)
        self.actor_list.append(self.camera_sensor)

    def set_sensor_back_camera(self):
        camera_blueprint = self.blueprint_library.find("sensor.camera.semantic_segmentation")
        camera_blueprint.set_attribute("image_size_x", f"{self.im_width}")
        camera_blueprint.set_attribute("image_size_y", f"{self.im_height}")
        camera_blueprint.set_attribute("fov", f"{self.im_fov}")
        cam_spawn_point = carla.Transform(carla.Location(x=-1.6, z=1.6), carla.Rotation(yaw=180.0))
        self.back_camera_sensor = self.world.spawn_actor(camera_blueprint, cam_spawn_point, attach_to=self.autopilot_vehicle,
                                                    attachment_type=carla.AttachmentType.Rigid)
        self.actor_list.append(self.back_camera_sensor)

    def set_sensor_left_camera(self):
        camera_blueprint = self.blueprint_library.find("sensor.camera.semantic_segmentation")
        camera_blueprint.set_attribute("image_size_x", f"{self.im_width}")
        camera_blueprint.set_attribute("image_size_y", f"{self.im_height}")
        camera_blueprint.set_attribute("fov", f"{self.im_fov}")
        cam_spawn_point = carla.Transform(carla.Location(x=1.6, y = -0.5 , z=1.6), carla.Rotation(yaw=-100.0))
        self.left_camera_sensor = self.world.spawn_actor(camera_blueprint, cam_spawn_point, attach_to=self.autopilot_vehicle,
                                                    attachment_type=carla.AttachmentType.Rigid)
        self.actor_list.append(self.left_camera_sensor)

    def set_sensor_right_camera(self):
        camera_blueprint = self.blueprint_library.find("sensor.camera.semantic_segmentation")
        camera_blueprint.set_attribute("image_size_x", f"{self.im_width}")
        camera_blueprint.set_attribute("image_size_y", f"{self.im_height}")
        camera_blueprint.set_attribute("fov", f"{self.im_fov}")
        cam_spawn_point = carla.Transform(carla.Location(x=1.6, y = 0.5 , z=1.6), carla.Rotation(yaw=100.0))
        self.right_camera_sensor = self.world.spawn_actor(camera_blueprint, cam_spawn_point, attach_to=self.autopilot_vehicle,
                                                    attachment_type=carla.AttachmentType.Rigid)
        self.actor_list.append(self.right_camera_sensor)

    def set_sensor_colision(self):
        colsensor_blueprint = self.blueprint_library.find("sensor.other.collision")
        colsensor_spawn_point = carla.Transform(carla.Location(x=0.0, z=0.5), carla.Rotation(yaw=0.0))
        self.colsensor = self.world.spawn_actor(colsensor_blueprint, colsensor_spawn_point,
                                                attach_to=self.autopilot_vehicle)
        self.actor_list.append(self.colsensor)

    def set_sensor_imu(self):
        imu_blueprint = self.blueprint_library.find("sensor.other.imu")
        imu_spawn_point = carla.Transform(carla.Location(x=0.0, z=0.5), carla.Rotation(yaw=0.0))
        self.imu_sensor = self.world.spawn_actor(imu_blueprint, imu_spawn_point, attach_to=self.autopilot_vehicle)
        self.actor_list.append(self.imu_sensor)

    def set_sensor_gnss(self):
        gnss_blueprint = self.blueprint_library.find("sensor.other.gnss")
        gnss_spawn_point = carla.Transform(carla.Location(x=0.0, z=0.5), carla.Rotation(yaw=0.0))
        self.gnss_sensor = self.world.spawn_actor(gnss_blueprint, gnss_spawn_point, attach_to=self.autopilot_vehicle)
        self.actor_list.append(self.gnss_sensor)

    def set_sensor_radar(self):
        radar_blueprint = self.blueprint_library.find("sensor.other.radar")
        radar_spawn_point = carla.Transform(carla.Location(x=0.0, z=0.5), carla.Rotation(yaw = 0.0))
        self.radar_sensor = self.world.spawn_actor(radar_blueprint, radar_spawn_point, attach_to = self.autopilot_vehicle)


    def spawn_npcs(self):
        for _, spawnpoint in zip(range(0,NPC_NUMBER), self.world.get_map().get_spawn_points()[:NPC_NUMBER+1]):
            npc_bp = random.choice(self.blueprint_library.filter("vehicle.*"))
            try:
                npc = self.world.spawn_actor(npc_bp, spawnpoint)
                npc.set_autopilot(True)
                self.actor_list.append(npc)
            except RuntimeError:
                pass

    def sensor_callback(self, data, queue):
        queue.put(data)

    def save_lidar_image(self, lidar_data):
        disp_size = [400,800]
        lidar_range = float(LIDAR_RANGE) * 2.0
        points = lidar_data
        points[:,:2] *= min(disp_size) / lidar_range
        points[:,:2] += (0.5 * disp_size[0], 0.5 * disp_size[1])
        points[:,:2] = np.fabs(points[:,:2])
        points = points.astype("int32")

        lidar_img_size = (disp_size[0],disp_size[1],3)
        lidar_img = np.zeros((lidar_img_size),dtype=np.int8)
        for point in points:
            if point[3] == 4:
                lidar_img[point[0]][point[1]] = [220,20,60]
            elif point[3] == 6:
                lidar_img[point[0]][point[1]] = [157,234,50]
            # elif point[3] == 1:
            #     lidar_img[point[0]][point[1]] = [70,70,70]
            # elif point[3] == 2:
            #     lidar_img[point[0]][point[1]] = [100,40,40]
            # elif point[3] == 3:
            #     lidar_img[point[0]][point[1]] = [55,90,80]
            elif point[3] == 7:
                lidar_img[point[0]][point[1]] = [128,64,128]
            # elif point[3] == 8:
            #     lidar_img[point[0]][point[1]] = [244,35,233]
            elif point[3] == 10:
                lidar_img[point[0]][point[1]] = [0,0,142]
            elif point[3] == 18:
                lidar_img[point[0]][point[1]] = [250,170,30]
            elif point[3] == 14:
                lidar_img[point[0]][point[1]] = [81,0,81]
            else:
                lidar_img[point[0]][point[1]] = [255,255,255]

            # lidar_img[point[0]][point[1]] = point[3]
        # lidar_img[tuple(points_t[:2])] = 250
        # print(lidar_img.shape)
        # img = Image.fromarray(lidar_img.astype("uint8"))
        lidar_img = np.flip(lidar_img, axis = 0)
        cv2.imshow("3", lidar_img)
        cv2.waitKey(1)
        return lidar_img

    def process_image_lidar_data(self, image_data, lidar_data, cv_number, side= "front"):
        if side == "front":
            image_w = self.camera_blueprint.get_attribute("image_size_x").as_int()
            image_h = self.camera_blueprint.get_attribute("image_size_y").as_int()
            fov = self.camera_blueprint.get_attribute("fov").as_float()
            focal = image_w / (2.0 * np.tan(fov * np.pi / 360.0))
            im_array = np.copy(np.frombuffer(image_data.raw_data, dtype=np.dtype("uint8")))
            im_array = np.reshape(im_array, (image_data.height, image_data.width, 4))
            im_array = im_array[:, :,2]  # taking only the RED values, since those describe objects in Carla(ie. 1-car, 2-sign...)
            # here we are eliminating unneeded objects from our semantic image, like buildings, sky, trees etc(converting them all to 0)
            # im_array = np.where(im_array == (1 or 2 or 3 or 5 or 9 or 11 or 12 or 13 or 14 or 15 or 16 or 17 or 19 or 20 or 21 or 22), 0, im_array)
            im_array2 = (im_array + im_array) * 5 # values go from 1-12(although we emmited 11 and 12, but i multiply them with 20 to get close
                                      # to grayscale pixel vlaue 0 - 255

            cv2.imshow(f"{cv_number}",im_array2)
            cv2.waitKey(1)

        image_w = self.camera_blueprint.get_attribute("image_size_x").as_int()
        image_h = self.camera_blueprint.get_attribute("image_size_y").as_int()
        fov = self.camera_blueprint.get_attribute("fov").as_float()
        focal = image_w / (2.0 * np.tan(fov * np.pi / 360.0))

        K = np.identity(3)
        K[0, 0] = K[1, 1] = focal
        K[0, 2] = image_w / 2.0
        K[1, 2] = image_h / 2.0

        im_array = np.copy(np.frombuffer(image_data.raw_data, dtype=np.dtype("uint8")))
        im_array = np.reshape(im_array, (image_data.height, image_data.width, 4))
        im_array = im_array[:, :,2]  # taking only the RED values, since those describe objects in Carla(ie. 1-car, 2-sign...)
        # here we are eliminating unneeded objects from our semantic image, like buildings, sky, trees etc(converting them all to 0)
        # im_array = np.where(im_array == (1 or 2 or 3 or 9 or 11 or 12), 0, im_array)
        # im_array = (im_array + im_array) * 5  # values go from 1-12(although we emmited 11 and 12, but i multiply them with 20 to get close
        # to grayscale pixel vlaue 0 - 255

        p_cloud_size = len(lidar_data)
        p_cloud = np.copy(np.frombuffer(lidar_data.raw_data, dtype=np.dtype('f4')))
        p_cloud = np.reshape(p_cloud, (p_cloud_size, 4))
        intensity = np.array(p_cloud[:, 3])
        local_lidar_points = np.array(p_cloud[:, :3]).T
        local_lidar_points = np.r_[
            local_lidar_points, [np.ones(local_lidar_points.shape[1])]]
        lidar_2_world = self.lidar_sensor.get_transform().get_matrix()

        world_points = np.dot(lidar_2_world, local_lidar_points)
        world_2_camera = np.array(self.camera_sensor.get_transform().get_inverse_matrix())
        sensor_points = np.dot(world_2_camera, world_points)

        point_in_camera_coords = np.array([
            sensor_points[1],
            sensor_points[2] * -1,
            sensor_points[0]])
        points_2d = np.dot(K, point_in_camera_coords)
        points_2d = np.array([
            points_2d[0, :] / points_2d[2, :],
            points_2d[1, :] / points_2d[2, :],
            points_2d[2, :]])
        points_2d = points_2d.T
        local_lidar_points = local_lidar_points.T

        for point_2d , lidar_point in zip(points_2d,local_lidar_points):

            if 0.0 < point_2d[0] < image_w and 0.0 < point_2d[1] < image_h and point_2d[2] > 0.0:
                u_coord = int(point_2d[0])
                v_coord = int(point_2d[1])
                object = im_array[v_coord, u_coord]
                lidar_point[3] = object
            else:
                lidar_point[3] = 0
        if side == "back":
            local_lidar_points[:,:2] = local_lidar_points[:,:2] * -1
        elif side == "left":
            theta = np.deg2rad(100)

            rot = np.array([[math.cos(theta), -math.sin(theta)], [math.sin(theta), math.cos(theta)]])
            local_lidar_points[:,:2] = np.dot(local_lidar_points[:,:2], rot)


        elif side == "right":
            theta = np.deg2rad(260)

            rot = np.array([[math.cos(theta), -math.sin(theta)], [math.sin(theta), math.cos(theta)]])
            local_lidar_points[:,:2] = np.dot(local_lidar_points[:,:2], rot)
        else:
            pass
        return local_lidar_points


    def reset(self):
        self.spawn_point = random.choice(self.map.get_spawn_points())
        self.autopilot_vehicle = self.world.spawn_actor(self.autopilot_bp, self.spawn_point)
        self.actor_list.append(self.autopilot_vehicle)
        time.sleep(0.5)
        self.set_sensor_camera()
        self.set_sensor_back_camera()
        self.set_sensor_left_camera()
        self.set_sensor_right_camera()
        self.set_sensor_colision()
        self.set_sensor_imu()
        self.set_sensor_gnss()
        self.set_sensor_lidar()
        self.set_sensor_back_lidar()
        self.set_sensor_left_lidar()
        self.set_sensor_right_lidar()
        time.sleep(0.5)
        self.spawn_npcs()

        self.camera_queue = Queue(maxsize=1)
        self.back_camera_queue = Queue(maxsize=1)
        self.left_camera_queue = Queue(maxsize=1)
        self.right_camera_queue = Queue(maxsize=1)
        self.imu_queue = Queue(maxsize=1)
        self.gnss_queue = Queue(maxsize=1)
        self.lidar_queue = Queue(maxsize=1)
        self.back_lidar_queue = Queue(maxsize=1)
        self.left_lidar_queue = Queue(maxsize=1)
        self.right_lidar_queue = Queue(maxsize=1)
        self.colision_queue = Queue(maxsize=1)
        self.camera_sensor.listen(lambda data: self.sensor_callback(data, self.camera_queue))
        self.back_camera_sensor.listen(lambda data: self.sensor_callback(data, self.back_camera_queue))
        self.left_camera_sensor.listen(lambda data: self.sensor_callback(data, self.left_camera_queue))
        self.right_camera_sensor.listen(lambda data: self.sensor_callback(data, self.right_camera_queue))
        self.imu_sensor.listen(lambda data: self.sensor_callback(data, self.imu_queue))
        self.gnss_sensor.listen(lambda data: self.sensor_callback(data, self.gnss_queue))
        self.lidar_sensor.listen(lambda data: self.sensor_callback(data, self.lidar_queue))
        self.back_lidar_sensor.listen(lambda data: self.sensor_callback(data, self.back_lidar_queue))
        self.left_lidar_sensor.listen(lambda data: self.sensor_callback(data, self.left_lidar_queue))
        self.right_lidar_sensor.listen(lambda data: self.sensor_callback(data, self.right_lidar_queue))
        self.colsensor.listen(lambda data: self.sensor_callback(data, self.colision_queue))
        self.autopilot_vehicle.set_autopilot(True)
        time.sleep(1)
        self.world.tick()

    def step(self,old_data):
        try:
            # Get the data once it's received from the queues
            camera_data = self.camera_queue.get(True, 1.0)
            back_camera_data = self.back_camera_queue.get(True, 1.0)
            left_camera_data = self.left_camera_queue.get(True, 1.0)
            right_camera_data = self.right_camera_queue.get(True, 1.0)
            lidar_data = self.lidar_queue.get(True, 1.0)
            back_lidar_data = self.back_lidar_queue.get(True, 1.0)
            left_lidar_data = self.left_lidar_queue.get(True, 1.0)
            right_lidar_data = self.right_lidar_queue.get(True, 1.0)
            imu_data = self.imu_queue.get(True, 1.0)
            gnss_data = self.gnss_queue.get(True, 1.0)

        except Empty:
            with self.colision_queue.mutex:
                self.colision_queue.queue.clear()
            with self.camera_queue.mutex:
                self.camera_queue.queue.clear()
            with self.back_camera_queue.mutex:
                self.back_camera_queue.queue.clear()
            with self.left_camera_queue.mutex:
                self.left_camera_queue.queue.clear()
            with self.right_camera_queue.mutex:
                self.right_camera_queue.queue.clear()
            with self.gnss_queue.mutex:
                self.gnss_queue.queue.clear()
            with self.imu_queue.mutex:
                self.imu_queue.queue.clear()
            with self.lidar_queue.mutex:
                self.lidar_queue.queue.clear()
            with self.back_lidar_queue.mutex:
                self.back_lidar_queue.queue.clear()
            with self.left_lidar_queue.mutex:
                self.left_lidar_queue.queue.clear()
            with self.right_lidar_queue.mutex:
                self.right_lidar_queue.queue.clear()
            print("[Warning] Some sensor data has been missed")

        new_lidar_data_forward = self.process_image_lidar_data(camera_data,lidar_data, 1)
        new_lidar_data_back = self.process_image_lidar_data(back_camera_data,back_lidar_data, 2, "back")
        new_lidar_data_left = self.process_image_lidar_data(left_camera_data,left_lidar_data,6, "left")
        new_lidar_data_right = self.process_image_lidar_data(right_camera_data,right_lidar_data,7,"right")
        # print(new_lidar_data.shape)
        new_lidar_data = np.concatenate((new_lidar_data_forward, new_lidar_data_back,
                                         new_lidar_data_left,new_lidar_data_right))
        # new_lidar_data = new_lidar_data_left
        combined_lidar_data = np.concatenate((new_lidar_data, old_data))
        image = self.save_lidar_image(combined_lidar_data)
        return new_lidar_data




if __name__ == "__main__":

        try:
            env = ENV()
            settings = env.world.get_settings()
            original_settings = env.world.get_settings()
            settings.synchronous_mode = True  # Enables synchronous mode
            settings.fixed_delta_seconds = 0.1  # 1 frame = 0.1 second
            env.world.apply_settings(settings)
            env.reset()
            old_lidar_data = [[0,0,0,0]]
            for _ in range(1,1000):

                old_lidar_data = env.step(old_lidar_data)

                env.world.tick()
        except KeyboardInterrupt:
            env.client.apply_batch([carla.command.DestroyActor(x) for x in env.actor_list])
            time.sleep(1)




        finally:
                # try:
                #     self.world.apply_settings(original_settings)
                # except NameError:
                #     pass

            env.client.apply_batch([carla.command.DestroyActor(x) for x in env.actor_list])

            time.sleep(3)
