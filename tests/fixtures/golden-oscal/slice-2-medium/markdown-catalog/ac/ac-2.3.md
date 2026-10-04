---
x-trestle-set-params:
  ac-02.03_odp.01:
    values:
  ac-02.03_odp.02:
    values:
x-trestle-global:
  sort-id: ac-02.03
---

# ac-2.3 - \[Access Control\] Disable Accounts

## Control Statement

Disable accounts within {{ insert: param, ac-02.03_odp.01 }} when the accounts:

- \[(a)\] Have expired;

- \[(b)\] Are no longer associated with a user or individual;

- \[(c)\] Are in violation of organizational policy; or

- \[(d)\] Have been inactive for {{ insert: param, ac-02.03_odp.02 }}.

## Control Assessment Objective

- \[AC-02(03)(a)\] accounts are disabled within {{ insert: param, ac-02.03_odp.01 }} when the accounts have expired;

- \[AC-02(03)(b)\] accounts are disabled within {{ insert: param, ac-02.03_odp.01 }} when the accounts are no longer associated with a user or individual;

- \[AC-02(03)(c)\] accounts are disabled within {{ insert: param, ac-02.03_odp.01 }} when the accounts are in violation of organizational policy;

- \[AC-02(03)(d)\] accounts are disabled within {{ insert: param, ac-02.03_odp.01 }} when the accounts have been inactive for {{ insert: param, ac-02.03_odp.02 }}.

## Control guidance

Disabling expired, inactive, or otherwise anomalous accounts supports the concepts of least privilege and least functionality which reduce the attack surface of the system.
