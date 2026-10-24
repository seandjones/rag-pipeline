Fictional company. Synthetic document created for RAG evaluation.

# Business Continuity and Disaster Recovery Plan

Version: 1.2
Effective date: January 15, 2026
Owner: VP of Engineering

## Purpose

This plan describes how Quillmark keeps its production platform and its essential business functions running through a disruption, and how it recovers when something fails. It sets the recovery targets the engineering organization works toward, explains how the platform is built to meet them, and defines how the arrangements are tested.

## Scope

The plan covers the production platform that customers use, the data it holds, the infrastructure it runs on, and the internal tools that engineers need in order to restore service. It addresses the loss of a facility, a region, a major component, or a key supplier, and the loss of access to the people or tools needed to run the platform. A security incident is handled under the Incident Response Plan, and this plan applies when the same event also takes the platform down.

## Roles and responsibilities

This plan is owned by the VP of Engineering. The VP of Engineering decides when a failover to the secondary region is called and is accountable for the platform meeting its recovery objectives. The on-call engineering lead directs the technical recovery and keeps the incident commander informed. The incident commander, as set out in the Incident Response Plan, coordinates communication within the company, and any notice to customers follows that plan. System owners maintain the recovery procedures for their own systems and take part in the tests. The Security team makes sure recovered systems return to service with their security controls in place.

## Policy

### Recovery objectives

The production platform has a recovery time objective (RTO) of 4 hours and a recovery point objective (RPO) of 1 hour. The RTO is the longest time the platform may be unavailable before service is restored. The RPO is the longest span of recent data that may be lost, which sets how current the recovered data must be. The recovery arrangements below are designed and tested against these objectives.

### Resilience of the platform

Production runs in a primary region and a secondary region, and the secondary region can take over all production traffic. The secondary region is kept ready to serve customers, with its data replicated so that the recovery point objective can be met. Components are built to tolerate failure wherever practical, and the dependencies that would stop the platform if they failed are listed in the recovery procedures together with the steps to work around them.

### Failover and recovery

When the primary region cannot serve customers, the VP of Engineering, advised by the on-call engineering lead, decides whether to move traffic to the secondary region. The decision is based on how serious the failure is and how long recovery in place would take. Engineers carry out the failover by following the written procedure, record each step as they go, and confirm that customers can use the platform before the failover is declared complete. Once the primary region is healthy again, traffic is moved back in a planned way and not in haste.

### Testing

A full disaster recovery failover test is performed annually. The test exercises the failover procedure from start to finish, measures the time taken and the data lost against the recovery objectives, and returns the platform to its normal arrangement afterwards.

Backup restore tests are performed quarterly. Each test restores data from a backup into a separate environment and checks that it is complete and usable. A backup that cannot be restored is treated as a failure of the backup, and the cause is fixed and the test is run again.

The results of every test are written up, and any shortfall against the recovery objectives becomes a tracked action with an owner.

### Communication during a disruption

The incident commander keeps leadership and staff informed in plain terms about what is affected and what is being done. Staff contact details for emergencies are kept outside the systems that might be down, so that the response team can still reach each other.

## Enforcement and review

The plan is reviewed annually and after every SEV-1 incident. Each review checks that the recovery objectives still suit the business, that the procedures match the platform as it is now, and that actions from earlier tests have been closed. Changes are approved by the Security Steering Committee, in line with the Information Security Policy.

A system owner who does not keep recovery procedures up to date or does not take part in testing is handled under the disciplinary provisions of the Information Security Policy.
