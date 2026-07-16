# Manual Assumptions Input Checklist

## Files

- Draft: `D:\codeprojects\family-office-ai-project\family-office-workspace\assumptions\base-assumptions.draft.json`
- Template reference: `D:\codeprojects\family-office-ai-project\family-office-workspace\assumptions\base-assumptions.template.json`
- Final private input to create: `base-assumptions.json`

## Required Values

- `personal.current_age`
- `personal.target_retirement_age`
- `cashflow.family_expenses_yearly`
- `cashflow.retirement_income_yearly` (optional; use `0` if none)
- `cashflow.net_salary_monthly`
- `cashflow.salary_months`
- `cashflow.spouse_net_salary_monthly` (optional; use `0` if none)
- `cashflow.spouse_salary_months` (optional; use `0` if none)
- `cashflow.rental_income_monthly_net` (optional; net monthly rent, use `0` if none)
- `returns.scenario`
- `returns.nominal_return`
- `returns.nominal_volatility` (required by Monte Carlo)

## Review Steps

1. Copy the draft structure to `base-assumptions.json`.
2. Replace every `null` with reviewed real assumptions.
3. Run `fo assumptions import`.
4. Run `fo assumptions check`.
5. Re-run net worth, retirement simulation and report.
