---
x-trestle-set-params:
  ma-4.1_prm_1:
    values:
  ma-04.01_odp.01:
    values:
  ma-04.01_odp.02:
    values:
x-trestle-global:
  sort-id: ma-04.01
---

# ma-4.1 - \[Maintenance\] Logging and Review

## Control Statement

- \[(a)\] Log {{ insert: param, ma-4.1_prm_1 }} for nonlocal maintenance and diagnostic sessions; and

- \[(b)\] Review the audit records of the maintenance and diagnostic sessions to detect anomalous behavior.

## Control Assessment Objective

- \[MA-04(01)(a)\]

  - \[MA-04(01)(a)[01]\] {{ insert: param, ma-04.01_odp.01 }} are logged for nonlocal maintenance sessions;
  - \[MA-04(01)(a)[02]\] {{ insert: param, ma-04.01_odp.02 }} are logged for nonlocal diagnostic sessions;

- \[MA-04(01)(b)\]

  - \[MA-04(01)(b)[01]\] the audit records of the maintenance sessions are reviewed to detect anomalous behavior;
  - \[MA-04(01)(b)[02]\] the audit records of the diagnostic sessions are reviewed to detect anomalous behavior.

## Control guidance

Audit logging for nonlocal maintenance is enforced by [AU-2](#au-2) . Audit events are defined in [AU-2a](#au-2_smt.a).
