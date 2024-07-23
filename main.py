# from src.ft.extract import Extractor

prompt_examples = {
    "prompts": [
        {
            "prompt": "Can you create a Service Catalog portfolio called Test_Portfolio? The dept is 1234, and the account id of the child aws account is 1234567890",
            "name": "Portfolio.json"
        },
        {
            "prompt": "Create an AWS CloudFormation template for a Service Catalog Product, the distributor should be 'App Vendor', and the support email 'https://www.support.example.com'",
            "name": "Product.json"
        },
        {
            "prompt": "Can you create an AWS CloudFormation template for an S3 bucket with server-side encryption, versioning enabled, and all public access blocked? The bucket should also have replication to another bucket and logging enabled.",
            "name": "compliant-bucket.json"
        },
        {
            "prompt": "Create an S3 bucket named 'my-unique-bucket' that allows cross-account access for the AWS account ID '123456789012' with encryption and versioning enabled.",
            "name": "s3-bucket-and-policy-for-caa-v1.json"
        },
        {
            "prompt": "Setup an S3 bucket which triggers a Lambda function on object creation, and ensure the Lambda has the necessary IAM role and permissions.",
            "name": "S3_LambdaTrigger.json"
        },
        {
            "prompt": "Create a secure static website using S3 and CloudFront. Include encrypted S3 buckets for content, logs, and replicas, enable versioning and replication, set up proper security headers and WAF integration, and ensure all resources comply with typical security standards.",
            "name": "compliant-static-website.json"
        },
        {
            "prompt": "Create an EMR cluster for Spark with the name 'emrcluster', m3.xlarge master and core instances, 2 core instances, in the subnet 'subnet-dba430ad', with logs stored in the 'emrclusterlogbucket' s3 bucket, and data in 'emrclusterdatabucket' bucket, and EMR release version 'emr-5.7.0'.",
            "name": "EMRClusterWithAdditionalSecurityGroups.json"
        },
        {
            "prompt": "Can you help me set up an EMR cluster with Spark and HBase, using specific instance types and an S3 bucket for HBase storage?",
            "name": "EMRCLusterGangliaWithSparkOrS3backedHbase.json"
        },
        {
            "prompt": "Deploy an AWS Neptune graph database cluster with provisions for customizing instance types, enabling encryption, setting up CloudWatch alarms for CPU, memory, and query performance, and configuring SNS notifications. Include the necessary IAM roles and policies for Neptune operations and audit logging. Also, ensure proper tagging for resources and allows for customization of maintenance windows and backup retention periods.",
            "name": "Neptune.json"
        },
        {
            "prompt": "Create an SNS topic with a subscription, where I can specify the endpoint and protocol for receiving notifications. The default protocol should be SQS.",
            "name": "SNSTopic.json"
        }
        
    ]
}

# ex = Extractor("include/cfrepo", None)

# ex.get_dataset()

from src.actions.deploy import DeployTFConfigAction
from src.db.supa import SupaClient
import os

c = SupaClient(3)
config = c.get_tf_config(10)

secret = os.environ.get("DEMO_AWS_SECRET_ACCESS_KEY", "")
access = os.environ.get("DEMO_AWS_ACCESS_KEY_ID", "")

action = DeployTFConfigAction(config, 10, c, secret, access, "testdir")