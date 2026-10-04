---
x-trestle-set-params:
  ma-04.04_odp:
    values:
x-trestle-global:
  sort-id: ma-04.04
---

# ma-4.4 - \[Maintenance\] Authentication and Separation of Maintenance Sessions

## Control Statement

Protect nonlocal maintenance sessions by:

- \[(a)\] Employing {{ insert: param, ma-04.04_odp }} ; and

- \[(b)\] Separating the maintenance sessions from other network sessions with the system by either:

  - \[(1)\] Physically separated communications paths; or
  - \[(2)\] Logically separated communications paths.

## Control Assessment Objective

- \[MA-04(04)(a)\] nonlocal maintenance sessions are protected by employing {{ insert: param, ma-04.04_odp }};

- \[MA-04(04)(b)\]

  - \[MA-04(04)(b)(01)\] nonlocal maintenance sessions are protected by separating maintenance sessions from other network sessions with the system by physically separated communication paths; or
  - \[MA-04(04)(b)(02)\] nonlocal maintenance sessions are protected by logically separated communication paths.

## Control guidance

Communications paths can be logically separated using encryption.
