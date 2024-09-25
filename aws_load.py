import boto3
from botocore.exceptions import ClientError
import sys
import time 
import os
import threading
import time
import requests
import queue


aws_access_key_id = os.environ.get('AWS_ACCESS_KEY_ID')
aws_secret_access_key = os.environ.get('AWS_SECRET_ACCESS_KEY')
aws_session_token = os.environ.get('AWS_SESSION_TOKEN')

print(aws_access_key_id)
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
        self.instances = []
        self.plugin_instances = {}
        self.round_robin_pointers = {}
        self.instance_lock = threading.Lock()
        self.task_queue = queue.Queue()
        # self.monitor_thread = threading.Thread(target=self.monitor_and_scale)
        # self.monitor_thread.daemon = True
        # self.monitor_thread.start()

    
    def start_new_instance(self, plugin_name):
        if plugin_name == 'DeepMake':
            user_script = f'''#!/bin/bash
            cd DeepMake
            uvicorn main:app --host 0.0.0.0 --port 8000'''
        else:
            user_script = f'''#!/bin/bash
            cd DeepMake
            uvicorn plugin.{plugin_name}.plugin:app --host 0.0.0.0 --port 8000'''
        # print(user_data)
        response = ec2_client.run_instances(
            ImageId='ami-05c1ffa5b02b5a4eb',  # Replace with  AMI ID
            InstanceType='t2.micro',  # Adjust based on needs
            # KeyName='Elasticache',
            MinCount=1,
            MaxCount=1,
            SecurityGroupIds=['sg-07c085041eb5bbc6a', 'sg-0b7b1fd9b8599217c', 'sg-0c058df2051cb3c0a'],
            SubnetId='subnet-0da0e54260ec33696',
            UserData= user_script,  # Adjust the UserData script to start application
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
        instance_id = response['Instances'][0]['InstanceId']
        print(f'Instance {instance_id} started')
        # Wait for the instance to be running and pass status checks
        ec2_client.get_waiter('instance_running').wait(InstanceIds=[instance_id])
        ec2_client.get_waiter('instance_status_ok').wait(InstanceIds=[instance_id])
        # Register the instance with the target group

        instance_list = ec2_client.describe_instances()['Reservations']
        for instance in instance_list:
            instance = instance['Instances'][0]
            if instance["InstanceId"] == instance_id:
                public_ip = instance["PublicIpAddress"]

        # Store instance info
        self.instances.append({'InstanceId': instance_id, 'LaunchTime': time.time(), 'InstanceType': plugin_name, 'InstanceIP': public_ip})

    def terminate_instance(self, instance):
        instance_id = instance['InstanceId']
        # Deregister the instance from the target group
        # Terminate the instance
        ec2_client.terminate_instances(InstanceIds=[instance_id])
        # Remove the instance from the list
        self.instances.remove(instance)


    

    def assign_instance(self, plugin_name):
        with instance_lock:
            instances = plugin_instances.get(plugin_name, [])
            if not instances:
                return None  # No instances available for this plugin
            # Initialize the round-robin pointer
            if plugin_name not in round_robin_pointers:
                round_robin_pointers[plugin_name] = 0
            # Get the index for the next instance
            index = round_robin_pointers[plugin_name]
            instance_info = instances[index]
            # Update the pointer for next time
            round_robin_pointers[plugin_name] = (index + 1) % len(instances)
            return instance_info

    def send_task_to_instance(self, instance, task):
        public_ip = instance['InstanceIP']
        endpoint = task['endpoint']
        json_data = task['json_data']
        url = f"http://{public_ip}:8000/plugins/call_endpoint/{task['plugin_name']}/{endpoint}"
        try:
            response = requests.put(url, json=json_data, timeout=240)
            response.raise_for_status()
            # Handle response as needed
        except requests.RequestException as e:
            print(f"Failed to send task to instance {instance['InstanceId']}: {e}")
            # Optionally handle failure


    def monitor_and_scale(self):
        while True:
            queue_size = task_queue.qsize()
            total_instances = len(instances)
            estimated_wait_time = calculate_wait_time(queue_size, total_instances)
            if estimated_wait_time > QUEUE_WAIT_THRESHOLD and total_instances < MAX_INSTANCES:
                # Scale up
                self.start_new_instance()
            elif total_instances > MIN_INSTANCES:
                # Check for instances to scale down
                for instance in instances:
                    usage = get_instance_usage(instance)
                    if usage < USAGE_THRESHOLD:
                        self.terminate_instance(instance)
            time.sleep(5)  # Check every 5 seconds

lb = LoadBalancer()
lb.start_new_instance("DeepMake")
print(lb.instances)
