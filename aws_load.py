import boto3
from botocore.exceptions import ClientError
import sys
import time 
import os
import threading
import time
import requests
import queue
import base64


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
        self.instance_lock = threading.Lock()
        self.task_queue = queue.Queue()
        # self.monitor_thread = threading.Thread(target=self.monitor_and_scale)
        # self.monitor_thread.daemon = True
        # self.monitor_thread.start()

    
    def start_new_instance(self, plugin_name):
        response = ec2_client.run_instances(
            ImageId='ami-05c1ffa5b02b5a4eb',  # Replace with  AMI ID
            InstanceType='t2.micro',  # Adjust based on needs
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
                        {'Key': 'Name', 'Value': 'PluginServer'},
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

    def task_dispatcher(self):
        while True:
            try:
                task = self.task_queue.get(timeout=1)
                plugin_name = task['plugin_name']
                user_id = task.get('user_id', 'anonymous')
                with instance_lock:
                    # Check if the user is already assigned to an instance
                    if user_id in user_instance_mapping:
                        instance_info = user_instance_mapping[user_id]
                    else:
                        # Assign an instance using round-robin
                        instances = self.instances.get(plugin_name, [])
                        if not instances:
                            # No instances available for this plugin
                            self.start_new_instance(plugin_name)
                            self.task_queue.put(task)  # Retry the task
                            continue

                        instance_info = self.assign_instance(plugin_name)
                        user_instance_mapping[user_id] = instance_info
                # Send the task to the assigned instance
                self.send_task_to_instance(instance_info, task)
                # Update instance usage
                update_instance_usage(instance_info)
            except:
                # No tasks in the queue
                time.sleep(1)
    

    def assign_instance(self, plugin_name):
        with instance_lock:
            instances = self.instances.get(plugin_name, [])
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
        public_ip = instance['InstanceIP']
        endpoint = task['endpoint']
        json_data = task['json_data']
        url = f"http://{public_ip}:8000/{endpoint}"
        try:
            response = requests.put(url, json=json_data, timeout=240)
            response.raise_for_status()
            # Handle response as needed
        except requests.RequestException as e:
            print(f"Failed to send task to instance {instance['InstanceId']}: {e}")
            # Optionally handle failure


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

# lb = LoadBalancer()
# lb.start_new_instance("DeepMake")
# print(lb.instances)
# lb.terminate_instance(lb.instances["DeepMake"]["running"][0])
