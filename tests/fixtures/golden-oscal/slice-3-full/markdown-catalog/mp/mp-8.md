---
x-trestle-set-params:
  mp-08_odp.01:
    values:
  mp-08_odp.02:
    values:
x-trestle-global:
  sort-id: mp-08
---

# mp-8 - \[Media Protection\] Media Downgrading

## Control Statement

- \[a.\] Establish {{ insert: param, mp-08_odp.01 }} that includes employing downgrading mechanisms with strength and integrity commensurate with the security category or classification of the information;

- \[b.\] Verify that the system media downgrading process is commensurate with the security category and/or classification level of the information to be removed and the access authorizations of the potential recipients of the downgraded information;

- \[c.\] Identify {{ insert: param, mp-08_odp.02 }} ; and

- \[d.\] Downgrade the identified system media using the established process.

## Control Assessment Objective

- \[MP-08a.\]

  - \[MP-08a.[01]\] a {{ insert: param, mp-08_odp.01 }} is established;
  - \[MP-08a.[02]\] the {{ insert: param, mp-08_odp.01 }} includes employing downgrading mechanisms with strength and integrity commensurate with the security category or classification of the information;

- \[MP-08b.\]

  - \[MP-08b.[01]\] there is verification that the system media downgrading process is commensurate with the security category and/or classification level of the information to be removed;
  - \[MP-08b.[02]\] there is verification that the system media downgrading process is commensurate with the access authorizations of the potential recipients of the downgraded information;

- \[MP-08c.\] {{ insert: param, mp-08_odp.02 }} is identified;

- \[MP-08d.\] the identified system media is downgraded using the {{ insert: param, mp-08_odp.01 }}.

## Control guidance

Media downgrading applies to digital and non-digital media subject to release outside of the organization, whether the media is considered removable or not. When applied to system media, the downgrading process removes information from the media, typically by security category or classification level, such that the information cannot be retrieved or reconstructed. Downgrading of media includes redacting information to enable wider release and distribution. Downgrading ensures that empty space on the media is devoid of information.
