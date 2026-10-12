# Employment income projection v1

`employment-income-projection/v1` is an internal, deterministic stage between
`work-transition-scenario/v1` and the later pension/bridge calculations. It does
not calculate or recommend a retirement date and does not request a target date.
The question-first command `fo planning work-transition plan` remains the
workspace-local readiness entry point. Once a monthly scenario and explicit
periodized bases are available, `fo planning work-transition projection build`
connects them to this deterministic stage and writes the snapshot inside the
workspace. The command never asks for a retirement or candidate cessation date.
Users should not edit the JSON contract manually.

## Supported calculations

- Periodized employment taxable bases must be explicitly marked `observed` or
  `declared`, with provenance. An illustrative national gross IRPEF amount may
  be shown only for a complete January–December 2026 scenario; it is explicitly
  **not** a person's total tax liability because other income, deductions,
  credits and surtaxes are excluded. Missing source verification date and the
  omitted taxable streams are blocking gaps.
- Pension-capital computation requires an explicitly supplied monthly base,
  an INPS management expressly supported by the versioned rule pack, and a
  sourced precision/rounding policy. The current pack does not enumerate those
  managements or rounding policy, so the amount remains `null` with a blocking
  gap. The 33% field is never employee withholding.
- Observed/declared TFR and complementary-pension amounts are passed through
  separately; the service does not derive TFR accrual or fund matching.

## Blocking gaps and limits

Payroll net, employee INPS withholding, employment deductions, regional and
municipal surtaxes, future-year pension contribution rates, projected TFR and
Fon.Te matching are not calculated. Missing inputs or rule coverage produce
explicit blocking `data_gaps`; partial-year income is never annualized into an
IRPEF result. 13th/14th-month payments are counted only if already included in
the explicit taxable base for the month they are paid; the service does not
infer or generate additional installments. Compensation and contribution/benefit policy references are not
resolved by this stage and therefore also remain blocking gaps. A blocked
projection must not feed a sustainable-exit date.

The service reads scenario and projection inputs only from
`family-office-workspace/` and writes its snapshot there. Synthetic fixtures in
tests are not household data.
