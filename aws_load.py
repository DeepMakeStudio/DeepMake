import boto3
import time
import os
import threading
import requests
import queue
from collections import deque

# AWS Credentials Configuration
aws_access_key_id = os.environ.get('AWS_ACCESS_KEY_ID')
aws_secret_access_key = os.environ.get('AWS_SECRET_ACCESS_KEY')
aws_session_token = os.environ.get('AWS_SESSION_TOKEN')

# Set up EC2 Client
ec2_client = boto3.client(
    'ec2',
    aws_access_key_id=aws_access_key_id,
    aws_secret_access_key=aws_secret_access_key,
    aws_session_token=aws_session_token,
    region_name="us-east-1"
)

# Configuration Constants
QUEUE_WAIT_THRESHOLD = 10  # Seconds
USAGE_THRESHOLD = 5        # Calls per minute per instance
MAX_INSTANCES = 10
MIN_INSTANCES = 1
COOLDOWN_PERIOD = 120      # Cooldown between scaling actions in seconds
IDLE_INSTANCE_THRESHOLD = 300  # Time in seconds before considering an instance for termination
INSTANCE_READY_TIMEOUT = 600    # Time in seconds to wait for an instance to become ready

# Custom queue class to track task wait times
class TimedQueue(queue.Queue):
    def put(self, item, block=True, timeout=None):
        item['enqueue_time'] = time.time()
        super().put(item, block, timeout)

    def get_wait_times(self):
        with self.mutex:
            current_time = time.time()
            return [current_time - task['enqueue_time'] for task in list(self.queue)]


class LoadBalancer:
    def __init__(self):
        self.instances = {}
        self.round_robin_pointers = {}
        self.running_tasks = {}
        self.ami_map = {"DeepMake": "ami-05c1ffa5b02b5a4eb", "Gsam": "ami-02279046f6b349605"}
        self.task_queue = {}
        for plugin in self.ami_map.keys():
            self.task_queue[plugin] = TimedQueue()

        self.instance_usage = {}  # Tracks instance usage
        self.instance_lock = threading.Lock()
        self.task_wait_times = deque(maxlen=100)  # Keep track of last 100 task wait times
        self.last_scale_up_time = 0
        self.last_scale_down_time = 0

        # Dictionary to track pending tasks to avoid duplicates
        self.pending_tasks = {}

        # Start Task Dispatcher
        self.task_thread = threading.Thread(target=self.task_dispatcher, args=("DeepMake",))
        self.task_thread.daemon = True
        self.task_thread.start()

        # self.task_thread = threading.Thread(target=self.task_dispatcher, args=("Gsam",))
        # self.task_thread.daemon = True
        # self.task_thread.start()

        # Start Monitor and Scale Thread
        # self.monitor_thread = threading.Thread(target=self.monitor_and_scale)
        # self.monitor_thread.daemon = True
        # self.monitor_thread.start()
        print("Load Balancer initialized and monitoring started.")

    def start_new_instance(self, plugin_name):
        ami = self.ami_map.get(plugin_name)
        if not ami:
            print(f"ERROR: No AMI found for plugin {plugin_name}")
            return
        response = ec2_client.request_spot_instances(
            LaunchSpecification={
            "ImageId": ami,  # Replace with  AMI ID
            "InstanceType": 'g4dn.xlarge',  # Adjust based on needs
            "KeyName": 'Elasticache',
            "SecurityGroupIds":['sg-07c085041eb5bbc6a', 'sg-0b7b1fd9b8599217c', 'sg-0c058df2051cb3c0a', 'sg-076f0dce9f923f9a4'],
            "SubnetId":'subnet-0da0e54260ec33696',
            # UserData= user_script,  # Adjust the UserData script to start application
            
            # MetadataOptions={
            #     'HttpTokens': 'required',
            # },
            # PrivateDnsNameOptions={
            #     'HostnameType': 'ip-name',
            #     'EnableResourceNameDnsARecord': True,
            #     'EnableResourceNameDnsAAAARecord': False
            # }
            },
            InstanceCount =  1,
            TagSpecifications=[
                {
                    'ResourceType': 'spot-instances-request',
                    'Tags': [
                        {'Key': 'Name', 'Value': plugin_name},
                    ]
                },
            ],

        )
        if plugin_name not in self.instances.keys():
            self.instances[plugin_name] = {"starting": [], "running": []}
        request_id = response['SpotInstanceRequests'][0]['SpotInstanceRequestId']
        request_list = ec2_client.describe_spot_instance_requests(SpotInstanceRequestIds=[request_id])
        while request_list["SpotInstanceRequests"][0]["State"] != "active":
            time.sleep(5)
            request_list = ec2_client.describe_spot_instance_requests(SpotInstanceRequestIds=[request_id])
        instance_id = request_list["SpotInstanceRequests"][0]["InstanceId"]
        print(instance_id)
        starting_instance = {'InstanceId': instance_id, 'LaunchTime': time.time()}
        with self.instance_lock:
            if plugin_name not in self.instances:
                self.instances[plugin_name] = {"starting": [], "running": []}
            self.instances[plugin_name]["starting"].append(starting_instance)

        # Handle instance transition in a separate thread to avoid blocking
        self.handle_instance_transition(plugin_name, instance_id)

    def handle_instance_transition(self, plugin_name, instance_id):
        """Transition instance from 'starting' to 'running'."""
        try:
            ec2_client.get_waiter('instance_running').wait(InstanceIds=[instance_id])
            ec2_client.get_waiter('instance_status_ok').wait(InstanceIds=[instance_id])
        except Exception as e:
            print(f"ERROR: Instance {instance_id} failed to transition to 'running' state: {e}")
            return
        
        print(f"INFO: Instance {instance_id} is now running. Updating instance list.")

        instance_list = ec2_client.describe_instances()["Reservations"]
        target_instance = None
        for instance in instance_list:
            if instance["Instances"][0]["InstanceId"] == instance_id:
                target_instance = instance
        if not target_instance:
            print(f"ERROR: Could not find instance {instance_id} in describe_instances response.")
        public_ip = target_instance['Instances'][0].get('PublicIpAddress', None)
        print(public_ip)
        if not public_ip:
            print(f"ERROR: Could not retrieve public IP for instance {instance_id}")
            return
        
        if plugin_name == "Gsam":
            while True:
                url = f"http://{public_ip}:8000/get_config"
                try: 
                    response = requests.get(url)
                    print(response.json())
                    if response.status_code == 200:
                        break
                except:
                    time.sleep(10)
                    continue

        with self.instance_lock:
            for instance in self.instances[plugin_name]["starting"]:
                if instance["InstanceId"] == instance_id:
                    self.instances[plugin_name]["running"].append({
                        'InstanceId': instance_id,
                        'LaunchTime': time.time(),
                        'InstanceType': plugin_name,
                        'InstanceIP': public_ip
                    })
                    self.instances[plugin_name]["starting"].remove(instance)
                    print(f"INFO: Instance {instance_id} for plugin {plugin_name} is now running with IP: {public_ip}")
                    break
        print(f"INFO: Instance {instance_id} is now running for plugin {plugin_name}")

    def terminate_instance(self, instance, plugin_name):
        instance_id = instance['InstanceId']
        ec2_client.terminate_instances(InstanceIds=[instance_id])
        with self.instance_lock:
            self.instances[plugin_name]["running"].remove(instance)
            if instance_id in self.instance_usage:
                del self.instance_usage[instance_id]
        print(f"INFO: Instance {instance_id} terminated for plugin {plugin_name}")

    def add_task(self, task):
        plugin_name = task['plugin_name']
        if plugin_name in self.pending_tasks:
            print(f"INFO: Task for plugin {plugin_name} is already pending. Skipping duplicate.")
            return
        task['enqueue_time'] = time.time()
        self.task_queue[plugin_name].put(task)
        print(f"INFO: Task added to queue for plugin {plugin_name}. Current queue size: {self.task_queue[plugin_name].qsize()}")

    def task_dispatcher(self, plugin_name):
        """Dispatches tasks to available instances."""
        while True:
            print("INFO: Checking for tasks in the queue...")
            task = self.task_queue[plugin_name].get()
            plugin_name = task['plugin_name']
            print(f"INFO: Dispatcher picked up task for plugin {plugin_name}. Current queue size after pickup: {self.task_queue[plugin_name].qsize()}")
            instances = self.instances.get(plugin_name, {"running": [], "starting": []})
            print("Instances: ", instances)
            # with self.instance_lock:
            if not instances["running"] and not instances["starting"]:
                print("A")
                print(f"INFO: No instances available for plugin {plugin_name}, starting a new one...")
                instance_thread = threading.Thread(target=self.start_new_instance, args=(plugin_name,))
                instance_thread.start()
                self.pending_tasks[plugin_name] = task  # Store the task as pending
                time.sleep(3)
                continue

            elif not instances["running"]:
                print("B")
                if plugin_name not in self.pending_tasks:
                    print(f"INFO: Plugin {plugin_name} instances are still starting up. Task is pending.")
                    self.pending_tasks[plugin_name] = task  # Store the task as pending
                time.sleep(3)
                continue
            print("C")
            # Assign a running instance to the task
            instance_info = self.assign_instance(plugin_name)
            print("Instance assigned: ", instance_info)
            self.pending_tasks.pop(plugin_name, None)  # Remove from pending since it will be processed now
            print(f"INFO: Task is being assigned to instance {instance_info['InstanceId']} for plugin {plugin_name}.")
            task_thread = threading.Thread(target=self.send_task_to_instance, args=(instance_info, task))
            task_thread.start()

    def assign_instance(self, plugin_name):
        with self.instance_lock:
            instances = self.instances.get(plugin_name, {"running": []})["running"]
            if not instances:
                return None
            if plugin_name not in self.round_robin_pointers:
                self.round_robin_pointers[plugin_name] = 0
            index = self.round_robin_pointers[plugin_name]
            instance_info = instances[index]
            self.round_robin_pointers[plugin_name] = (index + 1) % len(instances)
        return instance_info

    def send_task_to_instance(self, instance, task):
        print(f"INFO: Sending task to instance {instance['InstanceId']}")
        public_ip = instance['InstanceIP']
        url = f"http://{public_ip}:8000/{task['endpoint']}"
        try:
            self.running_tasks[task['plugin_name']] = task  # Mark the task as running
            response = requests.get(url) if 'json_data' not in task else requests.put(url, json=task['json_data'])
            print(f"INFO: Task sent successfully to instance {instance['InstanceId']}. Response: {response.json()}")
            self.running_tasks.pop(task['plugin_name'], None)  # Remove the task from running
        except Exception as e:
            print(f"ERROR: Failed to send task to instance {instance['InstanceId']}: {e}")

    def calculate_average_wait_time(self, plugin_name):
        wait_times = self.task_queue[plugin_name].get_wait_times()
        if wait_times:
            self.task_wait_times.extend(wait_times)
            return sum(self.task_wait_times) / len(self.task_wait_times)
        return 0

    def monitor_and_scale(self):
        while True:
            average_wait_time = 0
            for plugin_name in self.instances:
                average_wait_time += self.calculate_average_wait_time(plugin_name)
            total_instances = sum(len(self.instances[plugin]["running"]) for plugin in self.instances)
            current_time = time.time()

            print(f"INFO: Average wait time: {average_wait_time:.2f} seconds | Total Instances: {total_instances}")

            if average_wait_time > QUEUE_WAIT_THRESHOLD and total_instances < MAX_INSTANCES:
                for plugin_name in self.instances:
                    if current_time - self.last_scale_up_time > COOLDOWN_PERIOD:
                        print(f"INFO: Scaling up: Starting new instance for {plugin_name}.")
                        self.start_new_instance(plugin_name)
                        self.last_scale_up_time = current_time
                        break

            elif total_instances > MIN_INSTANCES:
                for plugin_name in self.instances:
                    for instance in self.instances[plugin_name]["running"][:]:
                        usage = len(self.instance_usage.get(instance['InstanceId'], []))
                        uptime = current_time - instance['LaunchTime']
                        if usage < USAGE_THRESHOLD and uptime > IDLE_INSTANCE_THRESHOLD:
                            if current_time - self.last_scale_down_time > COOLDOWN_PERIOD:
                                print(f"INFO: Scaling down: Terminating idle instance {instance['InstanceId']} for plugin {plugin_name}.")
                                self.terminate_instance(instance, plugin_name)
                                self.last_scale_down_time = current_time
                                break
            time.sleep(10)


# Test Code
if __name__ == "__main__":
    lb = LoadBalancer()
    lb.add_task({'plugin_name': 'DeepMake', 'endpoint': 'plugins/get_list'})
    # lb.add_task({'plugin_name': 'Gsam', 'endpoint': 'get_info'})
    while True:
        print(f"Running tasks: {lb.running_tasks}")
        # print(f"Instances: {lb.instances}")
        time.sleep(30)
