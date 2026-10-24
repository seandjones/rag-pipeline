Fictional company. Synthetic document created for RAG evaluation.

# Access Control Policy

Version: 2.0
Effective date: March 1, 2026
Owner: Chief Information Security Officer

This version supersedes Access Control Policy v1.0.

## Purpose

This policy defines how access to Quillmark systems and data is requested, approved, granted, reviewed, and removed. The aim is that people can do their work with the access they need and nothing beyond it, and that Quillmark can show who had access to what and why.

## Scope

The policy covers every account that touches a Quillmark system: workforce accounts for employees and contractors, accounts held by vendors, service accounts used by software, and administrator accounts. It applies to the production platform, to internal tools, and to the externally hosted applications that staff use for company work.

## Roles and responsibilities

The Chief Information Security Officer owns this policy and decides how it is applied when a situation is not covered. Each system has a system owner, a named person who decides who should have access to the system and is accountable for the accounts on it. Managers request access for the people they lead and confirm when that access is no longer needed. The Security team maintains the authentication standards and monitors for misuse of access. The People team records terminations in the HR system, which is the source of truth for when a person's employment or engagement ended.

## Policy

### Principles

Access is granted on the basis of need to know and least privilege. People receive the access their role requires, and access is tied to an individual so that every action can be attributed to a person. Access that was granted for a past task or a past role does not carry over to a new task or role.

### Requesting and approving access

Access requests must be approved by the requester's manager and by the system owner. The approvals are recorded with the request, and the team that administers the system grants only what the request describes. A person may not approve a request for their own access.

### Authentication

Multi-factor authentication (MFA) is required for all workforce accounts, including employees and contractors. The Security team publishes the list of approved authentication methods.

Administrators of production systems must use phishing-resistant MFA in the form of hardware security keys. The keys are issued by the Security team and registered to the individual administrator, and a lost key is reported at once so that it can be disabled.

### Passwords

Passwords must be at least 14 characters long. Passwords are not rotated on a fixed schedule; a password must be changed when compromise is suspected. The Security team screens new passwords against lists of known compromised passwords, and people are expected to use the approved password vault to create and keep their credentials rather than reusing them or writing them down.

### Lockout and sessions

Accounts are locked for 15 minutes after 10 consecutive failed login attempts. A pattern of lockouts on an account is reviewed by the Security team as a possible sign of an attack.

Production administration consoles end a session after 15 minutes of inactivity. Administrators sign in again with their authentication factors when a session has ended.

### Access reviews

User access reviews are performed quarterly by each system owner. The owner checks every account on the system, confirms that each person still needs the access they hold, and has anything unneeded removed. The completed review is recorded and made available to the Security team. Vendor user accounts are reviewed along with workforce accounts.

Privileged access is reviewed monthly. Anything that cannot be justified at the review is removed.

### Removing access

When a person leaves Quillmark, all of their access is revoked within 4 hours of the termination time recorded in the HR system. The system owner or the Security team confirms the revocation and looks for any access that was missed. When a person changes role, the access that belonged to the earlier role is removed as part of the move.

### Shared accounts and break-glass accounts

Shared accounts are prohibited for employees, contractors, and vendors, except for break-glass accounts. A break-glass account exists only for emergencies in which normal access is unavailable.

Break-glass account credentials are stored in the password vault, and every use is logged and reviewed within 1 business day. The reviewer confirms that the use was a genuine emergency.

## Enforcement and review

Violations of this policy are handled under the disciplinary provisions of the Information Security Policy. Access that has been granted outside the approval process is removed as soon as it is found, and the Security team records how it happened.

This policy is reviewed on the schedule set by the Information Security Policy and approved by the Security Steering Committee. The previous version is held separately and is not part of the current requirements.
