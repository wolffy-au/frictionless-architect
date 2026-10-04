---
x-trestle-set-params:
  cm-5.4_prm_1:
    values:
  cm-05.04_odp.01:
    values:
  cm-05.04_odp.02:
    values:
x-trestle-global:
  sort-id: cm-05.04
---

# cm-5.4 - \[Configuration Management\] Dual Authorization

## Control Statement

Enforce dual authorization for implementing changes to {{ insert: param, cm-5.4_prm_1 }}.

## Control Assessment Objective

- \[CM-05(04)[01]\] dual authorization for implementing changes to {{ insert: param, cm-05.04_odp.01 }} is enforced;

- \[CM-05(04)[02]\] dual authorization for implementing changes to {{ insert: param, cm-05.04_odp.02 }} is enforced.

## Control guidance

Organizations employ dual authorization to help ensure that any changes to selected system components and information cannot occur unless two qualified individuals approve and implement such changes. The two individuals possess the skills and expertise to determine if the proposed changes are correct implementations of approved changes. The individuals are also accountable for the changes. Dual authorization may also be known as two-person control. To reduce the risk of collusion, organizations consider rotating dual authorization duties to other individuals. System-level information includes operational procedures.
