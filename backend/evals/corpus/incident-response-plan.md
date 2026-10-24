Fictional company. Synthetic document created for RAG evaluation.

# Incident Response Plan

Version: 2.2
Effective date: February 1, 2026
Owner: Chief Information Security Officer

## Purpose

This plan describes how Quillmark detects, classifies, contains, and recovers from security incidents, and how it learns from them. It exists so that when something goes wrong, people know who is in charge, what to do, and who must be told, without having to work it out under pressure.

## Scope

The plan applies to any event that threatens the confidentiality, integrity, or availability of Quillmark information or of the production platform. That includes suspected and confirmed data breaches, malware, compromised accounts, lost equipment, and outages that have a security cause. Everyone who works for Quillmark, including contractors, is expected to report such events, and vendors are expected to report them under the Vendor Management Policy.

## Roles and responsibilities

The on-call security engineer responds to every reported incident and takes the initial report. The Chief Information Security Officer owns this plan and is the escalation point for serious incidents. The General Counsel advises on legal duties, decides what any notice to customers or regulators says, and decides who may speak publicly. The VP of Engineering provides the engineers who contain and repair affected systems. System owners help establish what was affected and carry out recovery on their systems. The Security team keeps the incident records and runs the exercises that keep this plan current.

## Policy

### Severity levels

Incidents are classified into four severity levels: SEV-1 (critical), SEV-2 (high), SEV-3 (moderate), and SEV-4 (low). A SEV-1 is a confirmed breach of Restricted data or a full outage of the production platform. The incident commander may raise or lower a classification as facts emerge, and the reason is written down.

### Detection and reporting

Incidents are found through automated monitoring, through reports from staff and customers, and through notices from vendors. Anyone who notices something suspicious reports it to the Security team at once. The on-call security engineer records the report, makes an initial assessment, and assigns a severity.

### Command and escalation

For a SEV-1, an incident commander must be assigned within 15 minutes of detection; for a SEV-2, within 1 hour. The on-call security engineer serves as incident commander and escalates every SEV-1 to the CISO immediately. The incident commander directs the response, keeps a running log of decisions and actions, and is the voice for status updates inside the company. SEV-3 and SEV-4 incidents are tracked and resolved by the on-call security engineer and are recorded in the same way as incidents of higher severity.

### Containment, eradication, and recovery

The response team limits the spread of the incident before anything else, for example by disabling accounts, isolating systems, or revoking credentials. Evidence is preserved so that the cause can be established later. The team then removes the cause, restores affected systems from known good sources, and watches the systems closely until the incident commander is satisfied that normal operation has returned. Where the production platform is down, recovery follows the Business Continuity and Disaster Recovery Plan.

### Customer and regulatory notification

When a breach of customer data is confirmed, Quillmark notifies affected customers within 72 hours of confirmation. The General Counsel decides what the notice says and whether any regulator must also be told. Notices state what happened, which data was involved, what Quillmark has done about it, and what customers should do to protect themselves.

### Postmortems

A blameless postmortem is required for every SEV-1 and SEV-2 incident and must be completed within 5 business days of resolution. The postmortem sets out the timeline, the cause, what worked, what did not, and the actions that follow, each with a named owner. Postmortems look at how systems and processes allowed the event, not at who made a mistake. The action items are tracked until they are done.

### Exercises and records

Tabletop exercises are held twice a year. Each exercise walks the response team through a realistic scenario and the findings are fed back into this plan. Incident records are retained for 3 years. A record includes the report, the severity decisions, the response log, and the postmortem where it was required.

## Enforcement and review

Failing to report a known or suspected incident is a breach of the Information Security Policy and is handled under its disciplinary provisions. Concealing an incident is treated as a serious matter.

The CISO reviews this plan on the schedule set by the Information Security Policy and after any incident that exposed a weakness in it. Changes are approved by the Security Steering Committee.
