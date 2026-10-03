---
x-trestle-set-params:
  cm-07.07_odp:
    values:
x-trestle-global:
  sort-id: cm-07.07
---

# cm-7.7 - \[Configuration Management\] Code Execution in Protected Environments

## Control Statement

Allow execution of binary or machine-executable code only in confined physical or virtual machine environments and with the explicit approval of {{ insert: param, cm-07.07_odp }} when such code is:

- \[(a)\] Obtained from sources with limited or no warranty; and/or

- \[(b)\] Without the provision of source code.

## Control Assessment Objective

the execution of binary or machine-executable code is only allowed in confined physical or virtual machine environments;

- \[CM-07(07)(a)\] the execution of binary or machine-executable code obtained from sources with limited or no warranty is only allowed with the explicit approval of {{ insert: param, cm-07.07_odp }};

- \[CM-07(07)(b)\] the execution of binary or machine-executable code without the provision of source code is only allowed with the explicit approval of {{ insert: param, cm-07.07_odp }}.

## Control guidance

Code execution in protected environments applies to all sources of binary or machine-executable code, including commercial software and firmware and open-source software.
