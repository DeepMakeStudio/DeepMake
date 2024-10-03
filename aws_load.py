import boto3
import time 
import os
import threading
import time
import requests
import queue
# from main import app, call_endpoint, huey
import asyncio

aws_access_key_id = os.environ.get('AWS_ACCESS_KEY_ID')
aws_secret_access_key = os.environ.get('AWS_SECRET_ACCESS_KEY')
aws_session_token = os.environ.get('AWS_SESSION_TOKEN')

ec2_client = boto3.client('ec2',
    aws_access_key_id=aws_access_key_id,
    aws_secret_access_key=aws_secret_access_key,
    aws_session_token = aws_session_token,
    region_name="us-east-1"
)
QUEUE_WAIT_THRESHOLD = 10  # Seconds
USAGE_THRESHOLD = 5  # Calls per minute per instance
MAX_INSTANCES = 10
MIN_INSTANCES = 1

# user_data = '''#!/bin/bash
# echo 'test' > /tmp/hello'''

class LoadBalancer:

    def __init__(self):
        self.instances = {}
        self.round_robin_pointers = {}
        self.task_queue = queue.Queue()
        self.task_thread = threading.Thread(target=self.task_dispatcher)
        self.task_thread.daemon = True
        self.task_thread.start()
        self.running_tasks = {}
        self.ami_map = {"DeepMake": "ami-05c1ffa5b02b5a4eb", "Gsam": "ami-02279046f6b349605"}
        # self.monitor_thread = threading.Thread(target=self.monitor_and_scale)
        # self.monitor_thread.daemon = True
        # self.monitor_thread.start()

    def start_new_instance(self, plugin_name):
        ami = self.ami_map.get(plugin_name, None)
        if ami is None:
            print("No AMI found for plugin")
            return
        print(ami)
        response = ec2_client.run_instances(
            ImageId=ami,  # Replace with  AMI ID
            InstanceType='g4dn.xlarge',  # Adjust based on needs
            KeyName='Elasticache',
            MinCount=1,
            MaxCount=1,
            SecurityGroupIds=['sg-07c085041eb5bbc6a', 'sg-0b7b1fd9b8599217c', 'sg-0c058df2051cb3c0a'],
            SubnetId='subnet-0da0e54260ec33696',
            # UserData= user_script,  # Adjust the UserData script to start application
            TagSpecifications=[
                {
                    'ResourceType': 'instance',
                    'Tags': [
                        {'Key': 'Name', 'Value': plugin_name},
                        {'Key': 'Plugin', 'Value': 'plugin-name'}
                    ]
                },
            ],
            MetadataOptions={
                'HttpTokens': 'required',
            },
            PrivateDnsNameOptions={
                'HostnameType': 'ip-name',
                'EnableResourceNameDnsARecord': True,
                'EnableResourceNameDnsAAAARecord': False
            }
        )
        if plugin_name not in self.instances.keys():
            self.instances[plugin_name] = {"starting": [], "running": []}
        instance_id = response['Instances'][0]['InstanceId']
        print(f'Instance {instance_id} started')
        starting_instance = {'InstanceId': instance_id, 'LaunchTime': time.time()}
        self.instances[plugin_name]["starting"].append(starting_instance)
        # Wait for the instance to be running and pass status checks
        ec2_client.get_waiter('instance_running').wait(InstanceIds=[instance_id])
        ec2_client.get_waiter('instance_status_ok').wait(InstanceIds=[instance_id])
        # Register the instance with the target group

        instance_list = ec2_client.describe_instances()['Reservations']
        for instance in instance_list:
            instance = instance['Instances'][0]
            if instance["InstanceId"] == instance_id:
                public_ip = instance["PublicIpAddress"]
                break

        # Store instance info
        self.instances[plugin_name]["running"].append({'InstanceId': instance_id, 'LaunchTime': time.time(), 'InstanceType': plugin_name, 'InstanceIP': public_ip})
        self.instances[plugin_name]["starting"].remove(starting_instance)
        print(self.instances)
        # self.instances.append({'InstanceId': instance_id, 'LaunchTime': time.time(), 'InstanceIP': public_ip})

    def terminate_instance(self, instance, plugin_name):
        instance_id = instance['InstanceId']
        # Deregister the instance from the target group
        # Terminate the instance
        ec2_client.terminate_instances(InstanceIds=[instance_id])
        # Remove the instance from the list
        self.instances[plugin_name]["running"].remove(instance)
    
    def add_task(self, task):
        self.task_queue.put(task)


    def task_dispatcher(self):
        while True:
            try:
                print("Checking for tasks")
                print(self.task_queue.qsize())
                task = self.task_queue.get()
                plugin_name = task['plugin_name']
                    # Check if the user is already assigned to an instance
                
                        # Assign an instance using round-robin
                instances = self.instances.get(plugin_name, [])
                if not instances or (len(instances["running"]) == 0 and len(instances["starting"]) == 0):
                    print("No instances available for this plugin")
                    # No instances available for this plugin
                    instance_thread = threading.Thread(target=self.start_new_instance, args=(plugin_name,))
                    instance_thread.start()
                    # self.start_new_instance(plugin_name)
                    self.add_task(task)  # Retry the task
                    time.sleep(3)
                    continue
                elif len(instances["running"]) == 0:
                    # Instance is starting up
                    print("Instance is starting up")
                    self.add_task(task)  # Retry the task
                    time.sleep(1)
                    continue

                print("Assigning instance")

                instance_info = self.assign_instance(plugin_name)
                print("Instance assigned: ", instance_info)
                # Send the task to the assigned instance

                task_thread = threading.Thread(target=self.send_task_to_instance, args=(instance_info, task))
                task_thread.start()
                # Update instance usage
                # update_instance_usage(instance_info)
            except Exception as e:
                print("Error in task dispatcher: ", str(e))

                # No tasks in the queue
                time.sleep(1)
    

    def assign_instance(self, plugin_name):
        instances = self.instances.get(plugin_name, [])["running"]
        if not instances:
            return None  # No instances available for this plugin
        # Initialize the round-robin pointer
        if plugin_name not in self.round_robin_pointers:
            self.round_robin_pointers[plugin_name] = 0
        # Get the index for the next instance
        index = self.round_robin_pointers[plugin_name]
        instance_info = instances[index]
        # Update the pointer for next time
        self.round_robin_pointers[plugin_name] = (index + 1) % len(instances)
        return instance_info

    def send_task_to_instance(self, instance, task):
        print("Sending task to instance")
        public_ip = instance['InstanceIP']
        endpoint = task['endpoint']
        json_data = task.get('json_data', None)
        plugin_name = task['plugin_name']
        url = f"http://{public_ip}:8000/{endpoint}"
        if plugin_name not in self.running_tasks.keys():
            self.running_tasks[plugin_name] = []
        self.running_tasks[plugin_name].append(task)

        try:
            if json_data is not None:
                response = requests.put(url, json=json_data)
            else:
                response = requests.get(url)
            print(response.json())
            # asyncio.run(call_endpoint(plugin_name, endpoint, json_data, public_ip))
            # Handle response as needed
        except Exception as e:
            print(f"Failed to send task to instance {instance['InstanceId']}: {e}")
            # Optionally handle failure
        self.running_tasks[plugin_name].remove(task)

    def monitor_and_scale(self):
        while True:
            queue_size = self.task_queue.qsize()
            total_instances = len(self.instances)
            estimated_wait_time = calculate_wait_time(queue_size, total_instances)
            if estimated_wait_time > QUEUE_WAIT_THRESHOLD and total_instances < MAX_INSTANCES:
                # Scale up
                self.start_new_instance()
            elif total_instances > MIN_INSTANCES:
                # Check for instances to scale down
                for instance in self.instances:
                    usage = get_instance_usage(instance)
                    if usage < USAGE_THRESHOLD:
                        self.terminate_instance(instance)
            time.sleep(5)  # Check every 5 seconds


lb = LoadBalancer()
# lb.start_new_instance("Gsam")
pseudo_instance = {'InstanceId': 'i-06bd0928fecfe0f51', 'LaunchTime': time.time(), 'InstanceType': 'Gsam', 'InstanceIP': '3.87.157.19'}
pseudo_task = {'plugin_name': 'Gsam', 'endpoint': 'get_info'}
lb.send_task_to_instance(pseudo_instance, pseudo_task)
while True:
    print(lb.running_tasks)
    time.sleep(10)
# lb.terminate_instance(lb.instances["DeepMake"]["running"][0])
