# S3 backend - run bootstrap.sh first to create the bucket
# terraform {
#   backend "s3" {
#     bucket         = "saas-platform-terraform-state-bucket"
#     key            = "terraform.tfstate"
#     region         = "eu-west-2"
#     encrypt        = true
#     dynamodb_table = "saas-platform-terraform-locks"
#   }
# }