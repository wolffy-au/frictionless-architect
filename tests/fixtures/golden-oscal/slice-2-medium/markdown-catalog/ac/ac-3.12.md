---
x-trestle-set-params:
  ac-03.12_odp:
    values:
x-trestle-global:
  sort-id: ac-03.12
---

# ac-3.12 - \[Access Control\] Assert and Enforce Application Access

## Control Statement

- \[(a)\] Require applications to assert, as part of the installation process, the access needed to the following system applications and functions: {{ insert: param, ac-03.12_odp }};

- \[(b)\] Provide an enforcement mechanism to prevent unauthorized access; and

- \[(c)\] Approve access changes after initial installation of the application.

## Control Assessment Objective

- \[AC-03(12)(a)\] as part of the installation process, applications are required to assert the access needed to the following system applications and functions: {{ insert: param, ac-03.12_odp }};

- \[AC-03(12)(b)\] an enforcement mechanism to prevent unauthorized access is provided;

- \[AC-03(12)(c)\] access changes after initial installation of the application are approved.

## Control guidance

Asserting and enforcing application access is intended to address applications that need to access existing system applications and functions, including user contacts, global positioning systems, cameras, keyboards, microphones, networks, phones, or other files.
