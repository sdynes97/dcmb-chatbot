terraform {
  required_version = ">= 1.9"

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 4.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.6"
    }
  }

  # Remote state stored in Azure Blob Storage.
  # Bootstrap this bucket once with scripts/bootstrap-tfstate.sh before running terraform init.
  backend "azurerm" {
    resource_group_name  = "dcmb-tfstate-rg"
    storage_account_name = "dcmbtfstate"
    container_name       = "tfstate"
    key                  = "dcmb-chatbot.tfstate"
  }
}

provider "azurerm" {
  features {}
  subscription_id = var.subscription_id
}
