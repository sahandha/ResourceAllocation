from google-api-python-client import container_v1

client = container_v1.ClusterManagerClient()

project_id = 'balmy-flash-135923'
zone = 'us-central1-a'

response = client.list_clusters(project_id, zone)
