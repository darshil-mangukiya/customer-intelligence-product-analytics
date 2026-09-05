#!/usr/bin/env Rscript

# Independent base-R validation of the deterministic synthetic retention experiment.
args <- commandArgs(trailingOnly = TRUE)
project_root <- if (length(args) >= 1) normalizePath(args[[1]], mustWork = TRUE) else normalizePath(getwd(), mustWork = TRUE)
input_path <- file.path(project_root, "data", "exports", "ab_test_customer_assignments.csv")
output_path <- file.path(project_root, "data", "exports", "r_experiment_validation.csv")

if (!file.exists(input_path)) stop(paste("Missing experiment input:", input_path))
experiment <- read.csv(input_path, stringsAsFactors = FALSE, check.names = FALSE)
required <- c("variant", "converted")
missing_columns <- setdiff(required, names(experiment))
if (length(missing_columns) > 0) stop(paste("Missing required columns:", paste(missing_columns, collapse = ", ")))

variants <- sort(unique(experiment$variant[!is.na(experiment$variant)]))
if (!identical(variants, sort(c("Control", "Retention Offer")))) stop("Expected exactly Control and Retention Offer variants")

converted <- tolower(trimws(as.character(experiment$converted)))
if (any(!converted %in% c("true", "false", "1", "0"))) stop("converted must contain boolean-like values")
experiment$converted_binary <- as.integer(converted %in% c("true", "1"))

control <- experiment[experiment$variant == "Control", , drop = FALSE]
treatment <- experiment[experiment$variant == "Retention Offer", , drop = FALSE]
control_n <- nrow(control)
treatment_n <- nrow(treatment)
if (min(control_n, treatment_n) <= 0) stop("Both experiment groups must be non-empty")

control_success <- sum(control$converted_binary)
treatment_success <- sum(treatment$converted_binary)
control_rate <- control_success / control_n
treatment_rate <- treatment_success / treatment_n
absolute_lift <- treatment_rate - control_rate
relative_lift <- if (control_rate == 0) NA_real_ else absolute_lift / control_rate
risk_ratio <- if (control_rate == 0) NA_real_ else treatment_rate / control_rate

# Match the Python two_proportion_test: pooled two-sided z test and unpooled Wald CI.
pooled_rate <- (control_success + treatment_success) / (control_n + treatment_n)
pooled_se <- sqrt(pooled_rate * (1 - pooled_rate) * (1 / control_n + 1 / treatment_n))
z_statistic <- if (pooled_se == 0) 0 else absolute_lift / pooled_se
prop_result <- prop.test(
  x = c(treatment_success, control_success),
  n = c(treatment_n, control_n),
  alternative = "two.sided",
  correct = FALSE
)
p_value <- unname(prop_result$p.value)
unpooled_se <- sqrt(control_rate * (1 - control_rate) / control_n + treatment_rate * (1 - treatment_rate) / treatment_n)
z_critical <- qnorm(0.975)
ci_lower <- absolute_lift - z_critical * unpooled_se
ci_upper <- absolute_lift + z_critical * unpooled_se

alpha <- 0.05
practical_threshold <- 0.02
result <- data.frame(
  analysis_name = "synthetic_retention_offer_v1",
  control_n = control_n,
  treatment_n = treatment_n,
  control_conversions = control_success,
  treatment_conversions = treatment_success,
  control_rate = control_rate,
  treatment_rate = treatment_rate,
  absolute_lift = absolute_lift,
  relative_lift = relative_lift,
  risk_ratio = risk_ratio,
  ci_lower = ci_lower,
  ci_upper = ci_upper,
  test_statistic = z_statistic,
  p_value = p_value,
  alpha = alpha,
  statistically_significant = p_value < alpha,
  practical_threshold = practical_threshold,
  practically_significant = abs(absolute_lift) >= practical_threshold,
  method = "Base R prop.test(correct=FALSE) pooled two-sided test; unpooled Wald CI matching Python",
  generated_at = format(Sys.time(), "%Y-%m-%dT%H:%M:%SZ", tz = "UTC"),
  data_provenance = "Deterministic synthetic experiment; no real customer experiment occurred",
  stringsAsFactors = FALSE
)

write.csv(result, output_path, row.names = FALSE, na = "")
cat(paste("R experiment validation written to", output_path, "\n"))
