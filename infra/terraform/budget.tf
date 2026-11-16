# Disabled until the administrator enables the Budget API and grants budget access.
# This watches the shared teaching project, including the other groups' spend.
variable "enable_budget_alert" {
  description = "Create the project budget and Anthony's email channel once access is available."
  type        = bool
  default     = false
}

resource "google_monitoring_notification_channel" "budget" {
  count        = var.enable_budget_alert ? 1 : 0
  display_name = "Group 6 - Anthony - budget projet"
  type         = "email"
  labels       = { email_address = "arascle@albertschool.com" }
  user_labels  = merge(local.common_labels, { component = "finops" })
}

# Billing budgets have no resource labels field. Scope is explicit in budget_filter.
resource "google_billing_budget" "project" {
  count           = var.enable_budget_alert ? 1 : 0
  billing_account = "0192F3-70E18D-2F5B30"
  display_name    = "Group 6 - veille du projet partage - 10 USD par mois"

  budget_filter {
    projects               = ["projects/671557693556"]
    calendar_period        = "MONTH"
    credit_types_treatment = "INCLUDE_ALL_CREDITS"
  }

  amount {
    specified_amount {
      currency_code = "USD"
      units         = "10"
    }
  }

  dynamic "threshold_rules" {
    for_each = [0.5, 0.9, 1.0]
    content {
      threshold_percent = threshold_rules.value
      spend_basis       = "CURRENT_SPEND"
    }
  }

  all_updates_rule {
    monitoring_notification_channels = [google_monitoring_notification_channel.budget[0].name]
    disable_default_iam_recipients   = true
  }
}
