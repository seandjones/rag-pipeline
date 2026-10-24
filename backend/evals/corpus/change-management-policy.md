Fictional company. Synthetic document created for RAG evaluation.

# Change Management Policy

Version: 2.1
Effective date: January 15, 2026
Owner: VP of Engineering

## Purpose

This policy governs how changes reach the Quillmark production platform. Outages and security problems can start with a change that nobody else looked at, so the policy requires that changes are reviewed, travel through a controlled path, and can be undone. It aims to let engineers ship quickly without putting customers at risk.

## Scope

The policy covers every change to production: application code, configuration, infrastructure, database structure, and the pipeline that deploys them. It applies to everyone who changes production, whether they are employees or contractors, and to every environment that serves customers. Changes to internal tools that do not touch production are governed by the working practices of the team that owns the tool.

## Roles and responsibilities

The VP of Engineering owns this policy and is accountable for engineering teams following it. Authors write and test their changes and explain what each change does and why. Reviewers examine changes with care and are accountable for what they approve. The on-call engineering lead approves emergency changes. The Security team maintains the pipeline's security controls and monitors for changes made outside it.

## Policy

### Code review and approval

Every production code change requires review and approval by at least one engineer other than the author. Reviewers look at whether the change does what it claims, whether it is tested, and whether it affects security, data handling, or other systems. Authors do not approve their own work, and a reviewer who has doubts says so and withholds approval until they are settled. Approval is recorded in the code repository, where it stays available for later inspection.

### Deployment path

Changes reach production only through the CI/CD pipeline; direct changes to production are prohibited except during an emergency. The pipeline builds the change, runs the automated tests, and checks for secrets and known weaknesses before it deploys. Access to deploy outside the pipeline is restricted, and any use of it is logged and reported to the Security team.

### Infrastructure changes

Infrastructure changes are made through infrastructure as code and follow the same review rules as application code. Engineers do not alter cloud resources by hand in the production environment. Where something has been changed by hand, the definition in code is corrected to match or the manual change is reversed, so that the code remains an accurate record.

### High-risk changes

High-risk changes must include a documented rollback plan. The rollback plan says how the change is to be undone, who decides to undo it, and how the team will know that it has worked. The reviewer checks the plan as part of the approval.

### Emergency changes

Emergency changes must be approved by the on-call engineering lead and reviewed within 2 business days after deployment. The after-the-fact review applies the same standard as an ordinary review, and anything it finds is corrected promptly. The reason for the emergency is written down.

### Change freeze

A production change freeze is in effect from December 20 through January 3 each year.

## Enforcement and review

Deploying to production outside this policy is a breach and is handled under the disciplinary provisions of the Information Security Policy. The Security team and the VP of Engineering look into any change that reached production without the required review or by a route other than the pipeline.

This policy is reviewed on the schedule set by the Information Security Policy. Changes are approved by the Security Steering Committee, and engineering teams are told of them before they take effect.
