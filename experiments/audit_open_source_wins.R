# Bounded external-reference check. Requires installed WINS and jsonlite.
# No package installation, random draws, model calls, or interval validation.
args <- commandArgs(trailingOnly = TRUE)
stopifnot(length(args) == 1L)
out_dir <- args[[1]]
dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)
stopifnot(requireNamespace("WINS", quietly = TRUE),
          requireNamespace("jsonlite", quietly = TRUE))

states <- expand.grid(success = c(0, 1), cost = c(0, .25, .5, 1, 2))
grid <- expand.grid(a = seq_len(nrow(states)), b = seq_len(nrow(states)),
                    tolerance = c(0, .25))
a <- states[grid$a, ]
b <- states[grid$b, ]
# This fixture's lower tier is eligible only when both workflows succeed.
# Recoding each failed workflow's cost to zero makes joint failures tie;
# discordant success has already been decided by the first endpoint.
pair_data <- data.frame(
  stratum = 1, pid_trt = grid$a, pid_con = grid$b,
  Delta_1_trt = 1, Delta_2_trt = 1, Delta_1_con = 1, Delta_2_con = 1,
  Y_1_trt = a$success, Y_2_trt = ifelse(a$success == 1, a$cost, 0),
  Y_1_con = b$success, Y_2_con = ifelse(b$success == 1, b$cost, 0))
score <- integer(nrow(grid))
tier <- rep(-1L, nrow(grid))
for (tol in c(0, .25)) {
  idx <- which(grid$tolerance == tol)
  ws <- WINS::win.strategy.default(pair_data[idx, ], priority = 1:2,
             tau = c(0, tol), np_direction = c("larger", "smaller"))
  score[idx] <- ws$Trt_Endpoint1 + ws$Trt_Endpoint2 -
                ws$Con_Endpoint1 - ws$Con_Endpoint2
  tier[idx] <- ifelse(ws$Trt_Endpoint1 + ws$Con_Endpoint1 > 0, 0L,
                ifelse(ws$Trt_Endpoint2 + ws$Con_Endpoint2 > 0, 1L, -1L))
}
rows <- data.frame(a_success = a$success, a_cost = a$cost,
                   b_success = b$success, b_cost = b$cost,
                   tolerance = grid$tolerance, score = score, tier = tier)
write.csv(rows, file.path(out_dir, "pair_scores.csv"), row.names = FALSE)

d <- data.frame(id = 1:8, arm = rep(c("A", "B"), each = 4), stratum = 1,
                Y_1 = c(1, 1, 1, 0, 1, 1, 0, 0),
                Y_2 = c(1, 2, 3, 0, .5, 1, 0, 0))
aggregate <- list()
for (reverse in c(FALSE, TRUE)) {
  arms <- if (reverse) c("B", "A") else c("A", "B")
  invisible(capture.output(r <- WINS::win.stat(
    d, ep_type = c("binary", "continuous"), arm.name = arms,
    priority = 1:2, np_direction = c("larger", "smaller"), tau = c(0, 0),
    method = "unadjusted", pvalue = "two-sided", summary.print = FALSE)))
  # Extract only fixed-n point summaries. Package intervals/p-values are unused.
  aggregate[[paste(arms, collapse = "_vs_")]] <- list(
    p_win = r$Win_prop$P_trt, p_loss = r$Win_prop$P_con,
    p_tie = 1 - r$Win_prop$P_trt - r$Win_prop$P_con,
    net_benefit = unname(r$Win_statistic$Net_Benefit[["NB"]]),
    win_ratio = unname(r$Win_statistic$Win_Ratio[["WR"]]),
    win_odds = unname(r$Win_statistic$Win_Odds[["WO"]]))
}
writeLines(deparse(WINS::win.strategy.default),
           file.path(out_dir, "installed_strategy.txt"))
jsonlite::write_json(list(
  R_version = R.version.string,
  WINS_version = as.character(utils::packageVersion("WINS")),
  WINS_license = utils::packageDescription("WINS")$License,
  jsonlite_version = as.character(utils::packageVersion("jsonlite")),
  aggregate = aggregate), file.path(out_dir, "external.json"),
  auto_unbox = TRUE, pretty = TRUE, digits = 16)
