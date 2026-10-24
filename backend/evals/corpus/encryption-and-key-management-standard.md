Fictional company. Synthetic document created for RAG evaluation.

# Encryption and Key Management Standard

Version: 1.3
Effective date: January 15, 2026
Owner: Platform Security team

## Purpose

This standard sets the minimum cryptographic protection for Quillmark data and describes how the keys behind that protection are created, stored, rotated, and retired. Encryption only helps if the algorithms are sound and the keys are well guarded, so the standard sets rules for each of them.

## Scope

The standard applies to all Quillmark data that is stored, moved, or processed on systems the company controls. It covers the production platform, internal systems, company laptops, and the software that engineers write and deploy. Vendors that hold Quillmark data are covered by the Vendor Management Policy.

## Roles and responsibilities

The Platform Security team owns key management. It also owns this standard, runs the key management service configuration, sets the approved algorithms and protocol settings, and keeps the key inventory. Engineering teams build and operate their services in line with the standard and ask the Platform Security team for keys rather than creating their own. System owners are accountable for the encryption of the systems assigned to them. The Security team monitors for weak or missing encryption and for exposed secrets. Whoever issues a company laptop enrolls it in device management before handing it over.

## Standard

### Data at rest

Data at rest, including databases, object storage, and backups, is encrypted with AES-256. Encryption is turned on when a storage location is created and is not left as a later task.

### Data in transit

Data in transit must use TLS 1.2 or higher, and TLS 1.3 is preferred. This applies to traffic from customers and to traffic between Quillmark services, and certificates must be issued and renewed by processes the Platform Security team has approved.

TLS 1.0 and TLS 1.1 are disabled on all Quillmark endpoints. If a customer integration depends on an older protocol, the owner raises it so that the customer can be helped to upgrade. The old protocol is not re-enabled to accommodate it.

### Key management

Encryption keys are managed in a cloud key management service, and customer data encryption keys are rotated annually or immediately when compromise is suspected. Keys are generated inside the service and never leave it in readable form. Access to keys is limited to the services and the people who need it, administrative actions on keys are logged, and the logs are reviewed by the Security team. Keys that are no longer needed are disabled and then destroyed. Rotation rules for other keys are set out in the key management procedures of the Platform Security team.

A suspected key compromise is reported as a security incident and handled under the Incident Response Plan.

### Company laptops

Company laptops must use full-disk encryption, enforced through mobile device management. A laptop that is not enrolled, or that falls out of compliance, loses access to company systems until it is brought back into line. A lost or stolen laptop is reported to the Security team at once so that its access can be revoked.

### Secrets

Secrets such as API keys and passwords must be stored in the secrets manager and never committed to source code. Applications retrieve secrets from the secrets manager when they run, and engineers do not copy them into configuration files, documents, or messages.

Secret scanning runs on every commit. When the scan finds a secret, the engineer removes it, the secret is treated as exposed and replaced, and the Security team is told so that it can check whether the secret was used.

## Enforcement and review

Any system found out of line with this standard is logged as a finding against its owner, who must fix it or obtain an exception through the security exceptions process described in the Information Security Policy. Violations by individuals are handled under the disciplinary provisions of that policy.

The Platform Security team reviews this standard on the schedule set by the Information Security Policy and whenever an algorithm or protocol it names is weakened or deprecated. Changes are approved by the Security Steering Committee.
