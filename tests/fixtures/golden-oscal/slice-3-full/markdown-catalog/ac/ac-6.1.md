---
x-trestle-set-params:
  ac-6.1_prm_2:
    values:
  ac-06.01_odp.01:
    values:
  ac-06.01_odp.02:
    values:
  ac-06.01_odp.03:
    values:
  ac-06.01_odp.04:
    values:
  ac-06.01_odp.05:
    values:
x-trestle-global:
  sort-id: ac-06.01
---

# ac-6.1 - \[Access Control\] Authorize Access to Security Functions

## Control Statement

Authorize access for {{ insert: param, ac-06.01_odp.01 }} to:

- \[(a)\] {{ insert: param, ac-6.1_prm_2 }} ; and

- \[(b)\] {{ insert: param, ac-06.01_odp.05 }}.

## Control Assessment Objective

- \[AC-06(01)(a)\]

  - \[AC-06(01)(a)[01]\] access is authorized for {{ insert: param, ac-06.01_odp.01 }} to {{ insert: param, ac-06.01_odp.02 }};
  - \[AC-06(01)(a)[02]\] access is authorized for {{ insert: param, ac-06.01_odp.01 }} to {{ insert: param, ac-06.01_odp.03 }};
  - \[AC-06(01)(a)[03]\] access is authorized for {{ insert: param, ac-06.01_odp.01 }} to {{ insert: param, ac-06.01_odp.04 }};

- \[AC-06(01)(b)\] access is authorized for {{ insert: param, ac-06.01_odp.01 }} to {{ insert: param, ac-06.01_odp.05 }}.

## Control guidance

Security functions include establishing system accounts, configuring access authorizations (i.e., permissions, privileges), configuring settings for events to be audited, and establishing intrusion detection parameters. Security-relevant information includes filtering rules for routers or firewalls, configuration parameters for security services, cryptographic key management information, and access control lists. Authorized personnel include security administrators, system administrators, system security officers, system programmers, and other privileged users.
