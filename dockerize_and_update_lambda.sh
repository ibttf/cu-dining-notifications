
# Get AWS account ID
export AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

# Clean up any existing images on my local docker
docker system prune -f

# Create ECR repository if it doesn't exist called cu-dining-notifications
# aws ecr describe-repositories --repository-names cu-dining-notifications || \
# aws ecr create-repository \
#     --repository-name cu-dining-notifications \
#     --image-scanning-configuration scanOnPush=true

# Get ECR login token
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin $AWS_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com

# Build and tag using buildx to specify a platform
docker buildx build --platform=linux/amd64 -t cu-dining-notifications --load .
docker tag cu-dining-notifications:latest $AWS_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/cu-dining-notifications:latest

# Push to ECR
docker push $AWS_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/cu-dining-notifications:latest   

aws lambda update-function-code \
    --function-name cu-dining-notifications-lambda \
    --image-uri $AWS_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/cu-dining-notifications:latest

# Update the memory size of the Lambda function
aws lambda update-function-configuration \
    --function-name cu-dining-notifications-lambda \
    --memory-size 2048
