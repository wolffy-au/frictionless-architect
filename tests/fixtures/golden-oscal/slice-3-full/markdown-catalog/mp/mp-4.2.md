---
x-trestle-set-params:
  mp-4.2_prm_1:
    values:
  mp-04.02_odp.01:
    values:
  mp-04.02_odp.02:
    values:
  mp-04.02_odp.03:
    values:
x-trestle-global:
  sort-id: mp-04.02
---

# mp-4.2 - \[Media Protection\] Automated Restricted Access

## Control Statement

Restrict access to media storage areas and log access attempts and access granted using {{ insert: param, mp-4.2_prm_1 }}.

## Control Assessment Objective

- \[MP-04(02)[01]\] access to media storage areas is restricted using {{ insert: param, mp-04.02_odp.01 }};

- \[MP-04(02)[02]\] access attempts to media storage areas are logged using {{ insert: param, mp-04.02_odp.02 }};

- \[MP-04(02)[03]\] access granted to media storage areas is logged using {{ insert: param, mp-04.02_odp.03 }}.

## Control guidance

Automated mechanisms include keypads, biometric readers, or card readers on the external entries to media storage areas.
