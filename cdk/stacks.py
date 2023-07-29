# Builtin
from os import getenv
from typing import Union, Dict, Any

# Third Party
from aws_cdk import Stack, Environment
from constructs import Construct
from aws_cdk.aws_cloudfront import CloudFrontAllowedMethods
from aws_cdk.aws_iam import CanonicalUserPrincipal
from aws_cdk.aws_s3_deployment import Source

# Library
from cdk import constructs
from cdk.enums import MyDomainName, CDKStackRegion, S3ResourcePolicyActions


class MyEnvironment(Environment):
    def __init__(self, *, account: str = None, region: str = None) -> None:
        account = getenv("CDK_DEFAULT_ACCOUNT") if not account else account
        region = getenv("CDK_DEFAULT_REGION") if not region else region
        super().__init__(account=account, region=region)


class MyStaticSiteStack(Stack):
    DOMAIN_NAME = MyDomainName.domain_name.value
    MY_ENV = MyEnvironment(region=CDKStackRegion.region.value)

    def __init__(
        self,
        scope: Construct,
        id: str,
        *,
        stack_name: str,
    ) -> None:
        super.__init__(scope, id, env=self.MY_ENV, stack_name=stack_name)

        # Create S3 bucket
        my_bucket: constructs.MyBucket = constructs.MyBucket(
            self,
            "my-domain-bucket",
            bucket_name=self.DOMAIN_NAME,
        )

        # Create domain certificate
        cert: constructs.MyCertificate = constructs.MyCertificate(
            self,
            "my-domain-certificate",
            domain_name=self.DOMAIN_NAME,
        )

        # Create Cloudfront user
        cloudfront_oai: constructs.MyCloudFrontOAI = constructs.MyCloudFrontOAI(
            self,
            id,
            comment=f"CloudFront OAI for {self.DOMAIN_NAME}"
        )

        # Add Cloudfront resource policy to bucket
        my_bucket.add_cloudfront_oai_to_policy(
            actions=S3ResourcePolicyActions.values,
            resources=[my_bucket.arn_for_objects("*")],
            principals=[
                CanonicalUserPrincipal(
                    cloudfront_oai.cloud_front_origin_access_identity_s3_canonical_user_id
                )
            ]
        )

        # Create viewer certificate
        viewer_cert = constructs.MyViewerCertificate(
            certificate=cert,
            aliases=[self.DOMAIN_NAME],
        )

        # Create CloudFront distribution
        distribution = constructs.MyDistribution(
            self,
            "my-cloudfront-distribution",
            s3_bucket_source=my_bucket,
            origin_access_identity=cloudfront_oai,
            allowed_methods=CloudFrontAllowedMethods.GET_HEAD_OPTIONS,
            viewer_certificate=viewer_cert,
        )

        # Create bucket deployment
        sources = [Source.asset("../src")]
        constructs.MyBucketDeployment(
            sources=sources,
            desination_bucket=my_bucket,
            distribution=distribution,
            distribution_paths=["/*"]
        )
