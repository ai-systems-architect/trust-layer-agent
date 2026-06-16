# AC-Family Compliance Assessment — DRAFT
**Run ID:** 5d3e845d-0394-4076-8d50-2bbe3e551ed2
**Account:** 123456789
**Controls:** AC-2, AC-3, AC-6, AC-17
**Assessment Date:** 2026-06-16
**Status:** DRAFT — Pending Authorizing Official Review
**Governance:** All evidence collected under trust ledger controls. Full audit trail in Langfuse trace 5d3e845d-0394-4076-8d50-2bbe3e551ed2.

---

# NIST 800-53 COMPLIANCE ASSESSMENT REPORT

**Run ID:** 5d3e845d-0394-4076-8d50-2bbe3e551ed2  
**Account Scope:** 123456789  
**Control Family:** AC (Access Control)  
**Assessment Date:** 2026-06-16  
**Assessor:** Federal Compliance Assessment Team

---

## EXECUTIVE SUMMARY

This assessment evaluated four NIST 800-53 Rev. 5 Access Control family controls (AC-2, AC-3, AC-6, AC-17) for AWS account 123456789. All four controls are determined to be **NON-COMPLIANT** based on documented policy violations, unauthorized access attempts, and missing security controls. Critical findings include over-privileged IAM roles with wildcard administrative permissions, dormant credential reactivation, privilege escalation attempts, and remote access configurations lacking multi-factor authentication requirements.

---

## CONTROL ASSESSMENTS

### AC-2: ACCOUNT MANAGEMENT

**DETERMINATION:** NON-COMPLIANT

**FINDING:**

The organization has failed to implement adequate account management controls as required by NIST 800-53 Rev. 5 AC-2. Three distinct violations were identified:

1. **Over-Privileged Role Configuration:** The DataAnalystRole possesses excessive permissions beyond its functional requirements. The role's attached DataAnalystPolicy grants broad access including "s3:*", "dynamodb:*", "rds:*", "lambda:*", and "glue:*" actions against all resources ("Resource": "*"), violating the principle of role-based access appropriate to job functions [Source: fixtures://iam_policies/ac2_over_privileged_role.json | Hash: 320600d8c5e0e3a9].

2. **Dormant Credential Reactivation:** A legacy service account (legacy-service-account) that had been inactive successfully authenticated via console login on 2024-11-01T09:23:11Z from IP address 203.0.113.42. The event metadata explicitly identifies this as a "dormant_credential_reactivated" finding, indicating failure to disable or remove accounts that are no longer required [Source: fixtures://cloudtrail_events/ac2_dormant_credential.json | Hash: 689bf666a1899e45].

3. **Account Security Compromise:** A console login event for test-user on 2025-04-01T10:00:00Z from IP 198.51.100.1 was flagged as an "injection_attempt" with control_id "AC-2", demonstrating inadequate account security controls and potential compromise of account credentials [Source: fixtures://cloudtrail_events/ac2_injection_attempt.json | Hash: a3b116bab805073c].

These findings collectively demonstrate non-compliance with AC-2 requirements for managing information system accounts including identification, authorization, monitoring, and disabling of accounts.

**REMEDIATION RECOMMENDATIONS:**

1. **Immediate Actions (0-30 days):**
   - Disable the legacy-service-account immediately and conduct forensic review of all actions taken during the 2024-11-01 session
   - Revoke and rotate credentials for test-user and investigate the injection attempt incident
   - Implement automated account lifecycle management to identify and disable dormant accounts after 90 days of inactivity

2. **Short-term Actions (30-90 days):**
   - Refactor DataAnalystRole permissions to implement least-privilege access using specific resource ARNs and limiting actions to only those required for data analysis functions (e.g., s3:GetObject, s3:ListBucket on specific analytics buckets)
   - Implement IAM Access Analyzer to continuously monitor for over-privileged roles
   - Establish quarterly access reviews for all IAM principals with documented approval workflows

3. **Long-term Actions (90-180 days):**
   - Deploy AWS Organizations Service Control Policies (SCPs) to prevent creation of over-privileged roles
   - Implement automated account provisioning and deprovisioning integrated with HR systems
   - Establish continuous monitoring with automated alerts for dormant account reactivation and suspicious authentication patterns

---

### AC-3: ACCESS ENFORCEMENT

**DETERMINATION:** NON-COMPLIANT

**FINDING:**

The organization has failed to enforce approved authorizations for logical access to information and system resources as required by NIST 800-53 Rev. 5 AC-3. Two critical deficiencies were identified:

1. **Missing Permission Boundaries:** The DeveloperRole is configured with IAM permissions to create roles and attach role policies ("iam:CreateRole", "iam:AttachRolePolicy") against all resources ("Resource": "*") without any permission boundaries or session policies to constrain the scope of access. This configuration allows developers to escalate their own privileges by creating new roles with arbitrary permissions, effectively bypassing access enforcement mechanisms [Source: fixtures://iam_policies/ac3_missing_boundary_policy.json | Hash: ee6f2d2c706edbd9].

2. **Unauthorized Access Attempt with Insufficient Enforcement:** On 2025-01-15T14:45:33Z, the DeveloperRole attempted to access an S3 object (pii/customer-records.csv) in the prod-sensitive-data bucket. While this specific attempt resulted in an "AccessDenied" error, the fact that the role was able to make the request indicates insufficient preventive controls. The role should not have network or logical access paths to production sensitive data resources in the first place [Source: fixtures://cloudtrail_events/ac3_unauthorized_access_attempt.json | Hash: 927f8ff5ff833cb3].

These findings demonstrate that access enforcement mechanisms are inadequately configured to prevent unauthorized access and privilege escalation, constituting non-compliance with AC-3 requirements.

**REMEDIATION RECOMMENDATIONS:**

1. **Immediate Actions (0-30 days):**
   - Implement IAM permission boundaries on all developer roles to prevent privilege escalation through role creation/modification
   - Conduct audit of all roles created by DeveloperRole since deployment and revoke any that violate least privilege
   - Implement S3 bucket policies and VPC endpoints to enforce network-level isolation between development and production environments

2. **Short-term Actions (30-90 days):**
   - Refactor DeveloperRole to remove iam:CreateRole and iam:AttachRolePolicy permissions; implement Infrastructure-as-Code (IaC) approval workflow for role creation
   - Deploy AWS IAM Access Analyzer policy validation in CI/CD pipelines to prevent deployment of overly permissive policies
   - Implement attribute-based access control (ABAC) using resource tags to enforce environment-based access restrictions

3. **Long-term Actions (90-180 days):**
   - Establish centralized access control governance using AWS Organizations SCPs to enforce permission boundaries organization-wide
   - Implement zero-trust architecture with explicit deny policies for cross-environment access
   - Deploy continuous compliance monitoring with automated remediation for policy violations

---

### AC-6: LEAST PRIVILEGE

**DETERMINATION:** NON-COMPLIANT

**FINDING:**

The organization has failed to employ the principle of least privilege as required by NIST 800-53 Rev. 5 AC-6. Two severe violations were identified:

1. **Wildcard Administrative Access:** The LegacyAdminRole is configured with the AWS-managed AdministratorAccess policy, which grants "Action": "*" and "Resource": "*" permissions. This provides unrestricted access to all AWS services and resources, violating the fundamental principle of least privilege by granting far more access than necessary for any legitimate administrative function [Source: fixtures://iam_policies/ac6_wildcard_admin.json | Hash: a4db0b7a3349019c].

2. **Privilege Escalation Execution:** On 2025-02-20T11:12:44Z, the DeveloperRole successfully executed an AttachRolePolicy action to attach the AdministratorAccess policy (arn:aws:iam::aws:policy/AdministratorAccess) to itself (roleName: "DeveloperRole"). This represents an actual privilege escalation event where a non-privileged role elevated its own permissions to full administrative access, demonstrating both excessive initial permissions and failure to prevent privilege escalation [Source: fixtures://cloudtrail_events/ac6_privilege_escalation.json | Hash: 007ac958e5406ec9].

These findings demonstrate systematic failure to implement least privilege controls, with both policy misconfigurations enabling excessive access and documented exploitation of those misconfigurations to escalate privileges.

**REMEDIATION RECOMMENDATIONS:**

1. **Immediate Actions (0-30 days):**
   - Revoke AdministratorAccess policy from LegacyAdminRole and DeveloperRole immediately
   - Conduct forensic investigation of all actions performed by DeveloperRole between 2025-02-20T11:12:44Z and policy revocation
   - Implement AWS CloudTrail alerts for any AttachRolePolicy, PutRolePolicy, or CreateRole actions
   - Enable MFA delete and MFA-required conditions for all privileged operations

2. **Short-term Actions (30-90 days):**
   - Replace LegacyAdminRole with function-specific administrative roles (e.g., NetworkAdminRole, SecurityAdminRole) with scoped permissions
   - Implement IAM permission boundaries on all roles to prevent self-modification and privilege escalation
   - Deploy AWS Config rules to detect and automatically remediate wildcard administrative policies
   - Establish break-glass emergency access procedures using AWS SSO with time-limited elevated access

3. **Long-term Actions (90-180 days):**
   - Implement just-in-time (JIT) privileged access management requiring approval workflows for elevated permissions
   - Establish quarterly least-privilege reviews using IAM Access Analyzer findings to identify and remove unused permissions
   - Deploy Service Control Policies (SCPs) to prevent attachment of AdministratorAccess policy except by designated security team roles
   - Implement session policies to further constrain temporary elevated access even when granted

---

### AC-17: REMOTE ACCESS

**DETERMINATION:** NON-COMPLIANT

**FINDING:**

The organization has failed to establish and document usage restrictions, configuration requirements, and implementation guidance for remote access as required by NIST 800-53 Rev. 5 AC-17. Specifically, multi-factor authentication (MFA) is not consistently enforced for remote access:

1. **Remote Access Policy Without MFA Requirement:** The RemoteAccessRole is configured with permissions to initiate remote sessions (ssm:StartSession, ec2:DescribeInstances) without any conditional requirements for MFA. The policy document contains no "Condition" block requiring "aws:MultiFactorAuthPresent": "true", allowing remote access to EC2 instances without multi-factor authentication [Source: fixtures://iam_policies/ac17_remote_access_no_mfa.json | Hash: 5c237cf82659d42a].

2. **Remote Session Executed Without MFA:** On 2025-03-10T08:30:22Z, the RemoteAccessRole successfully initiated a StartSession event to EC2 instance i-0abc123def456789. The userIdentity context explicitly shows "mfaAuthenticated": "false", confirming that remote access was granted and executed without multi-factor authentication [Source: fixtures://cloudtrail_events/ac17_remote_session_no_mfa.json | Hash: 6326295d9b0e415c].

While evidence shows that a compliant configuration exists (RemoteAccessRoleCompliant with MFA conditions in policy [Source: fixtures://iam_policies/ac17_remote_access_with_mfa.json | Hash: 5d0a753631511cda] and corresponding MFA-authenticated session [Source: fixtures://cloudtrail_events/ac17_remote_session_with_mfa.json | Hash: ba036f4475ce36fa]), the presence of non-compliant remote access mechanisms constitutes a control failure. AC-17 requires that all remote access methods enforce organizational security requirements, not merely that compliant options exist alongside non-compliant ones.

**REMEDIATION RECOMMENDATIONS:**

1. **Immediate Actions (0-30 days):**
   - Revoke RemoteAccessRole or modify its trust policy to require MFA for role assumption
   - Add IAM policy conditions requiring "aws:MultiFactorAuthPresent": "true" for all SSM StartSession actions
   - Audit all remote access sessions from the past 90 days to identify sessions without MFA and review actions taken
   - Implement AWS Config rule to detect IAM policies allowing remote access without MFA conditions

2. **Short-term Actions (30-90 days):**
   - Deprecate RemoteAccessRole and migrate all users to RemoteAccessRoleCompliant
   - Implement AWS SSO with mandatory MFA enrollment for all users requiring remote access
   - Deploy Session Manager preferences to enforce additional session encryption and logging requirements
   - Establish automated remediation to add MFA conditions to any remote access policies deployed without them

3. **Long-term Actions (90-180 days):**
   - Implement Service Control Policies (SCPs) at the AWS Organizations level to prevent creation of remote access policies without MFA requirements
   - Deploy hardware MFA tokens (FIDO2/WebAuthn) for all privileged users to prevent MFA bypass attacks
   - Establish continuous monitoring dashboard for remote access sessions with real-time alerting for non-MFA sessions
   - Implement certificate-based authentication for Systems Manager sessions as additional authentication factor

---

## EVIDENCE CITATIONS

The following evidence sources were cited in this assessment:

### IAM Policy Documents
- `fixtures://iam_policies/ac2_over_privileged_role.json` | Hash: `320600d8c5e0e3a9`
- `fixtures://iam_policies/ac3_missing_boundary_policy.json` | Hash: `ee6f2d2c706edbd9`
- `fixtures://iam_policies/ac6_wildcard_admin.json` | Hash: `a4db0b7a3349019c`
- `fixtures://iam_policies/ac17_remote_access_no_mfa.json` | Hash: `5c237cf82659d42a`
- `fixtures://iam_policies/ac17_remote_access_with_mfa.json` | Hash: `5d0a753631511cda`

### CloudTrail Events
- `fixtures://cloudtrail_events/ac2_dormant_credential.json` | Hash: `689bf666a1899e45`
- `fixtures://cloudtrail_events/ac2_injection_attempt.json` | Hash: `a3b116bab805073c`
- `fixtures://cloudtrail_events/ac3_unauthorized_access_attempt.json` | Hash: `927f8ff5ff833cb3`
- `fixtures://cloudtrail_events/ac6_privilege_escalation.json` | Hash: `007ac958e5406ec9`
- `fixtures://cloudtrail_events/ac17_remote_session_no_mfa.json` | Hash: `6326295d9b0e415c`
- `fixtures://cloudtrail_events/ac17_remote_session_with_mfa.json` | Hash: `ba036f4475ce36fa`

### NIST 800-53 Reference Documentation
- `nist_800_53` | Hash: `115261d6b194313a` (AC-2 control definition)
- `nist_800_53` | Hash: `69e9ceebf47060f8` (AC-3 control enhancements)
- `nist_800_53` | Hash: `72e1cda161aa7a53` (AC-6 control enhancements)
- `nist_800_53` | Hash: `642ad3987a9265d9` (AC-17 control enhancements)

---

## PRIORITIZED RECOMMENDATIONS

### CRITICAL PRIORITY (Immediate - 0-30 Days)

1. **Revoke Escalated Privileges and Conduct Forensic Investigation**
   - **Controls:** AC-6, AC-3
   - **Action:** Immediately revoke AdministratorAccess from DeveloperRole and LegacyAdminRole; conduct forensic review of all actions taken by DeveloperRole since 2025-02-20T11:12:44Z
   - **Rationale:** Active privilege escalation represents immediate security risk with potential for data exfiltration, resource manipulation, or further compromise

2. **Disable Dormant and Compromised Accounts**
   - **Controls:** AC-2
   - **Action:** Disable legacy-service-account and test-user; rotate all credentials; investigate injection attempt and dormant credential reactivation incidents
   - **Rationale:** Compromised credentials provide adversaries with authenticated access to organizational resources

3. **Enforce MFA for Remote Access**
   - **Controls:** AC-17
   - **Action:** Add IAM policy conditions requiring MFA for all remote access roles; revoke or modify RemoteAccessRole to require MFA
   - **Rationale:** Remote access without MFA is a primary attack vector for unauthorized access

4. **Implement Permission Boundaries**
   - **Controls:** AC-3, AC-6
   - **Action:** Deploy IAM permission boundaries on all non-administrative roles to prevent privilege escalation through role creation/modification
   - **Rationale:** Prevents recurrence of documented privilege escalation attack

### HIGH PRIORITY (Short-term - 30-90 Days)

5. **Refactor Over-Privileged Roles to Least Privilege**
   - **Controls:** AC-2, AC-6
   - **Action:** Redesign DataAnalystRole, DeveloperRole, and LegacyAdminRole with specific resource ARNs and minimum required actions
   - **Rationale:** Reduces attack surface and limits blast radius of credential compromise

6. **Implement Automated Account Lifecycle Management**
   - **Controls:** AC-2
   - **Action:** Deploy automated detection and disabling of dormant accounts after 90 days; integrate with HR systems for automated deprovisioning
   - **Rationale:** Prevents accumulation of unused credentials that can be exploited

7. **Deploy Continuous Compliance Monitoring**
   - **Controls:** AC-2, AC-3, AC-6, AC-17
   - **Action:** Implement AWS Config rules, IAM Access Analyzer, and CloudWatch alarms for policy violations with automated remediation
   - **Rationale:** Provides real-time detection and response to configuration drift and policy violations

8. **Establish Network-Level Access Isolation**
   - **Controls:** AC-3
   - **Action:** Implement VPC endpoints, security groups, and S3 bucket policies to enforce network isolation between development and production environments
   - **Rationale:** Provides defense-in-depth by preventing unauthorized access attempts at network layer

### MEDIUM PRIORITY (Long-term - 90-180 Days)

9. **Implement Organization-Wide Governance Controls**
   - **Controls:** AC-2, AC-3, AC-6, AC-17
   - **Action:** Deploy AWS Organizations Service Control Policies (SCPs) to enforce security baselines across all accounts
   - **Rationale:** Prevents non-compliant configurations from being deployed in any organizational account

10. **Establish Just-in-Time Privileged Access Management**
    - **Controls:** AC-6
    - **Action:** Implement JIT access workflows requiring approval for time-limited elevated permissions
    - **Rationale:** Reduces standing privileges and provides audit trail for privileged operations

11. **Deploy Zero-Trust Architecture**
    - **Controls:** AC-3, AC-17
    - **Action:** Implement attribute-based access control (ABAC), certificate-based authentication, and explicit deny policies for cross-environment access
    - **Rationale:** Establishes comprehensive access control framework based on continuous verification

12. **Implement Quarterly Access Reviews**
    - **Controls:** AC-2, AC-6
    - **Action:** Establish formal access review process using IAM Access Analyzer findings with documented approval workflows
    - **Rationale:** Ensures ongoing compliance and identifies permission creep over time

---

## ASSESSMENT CONCLUSION

This assessment identified systemic non-compliance across all four evaluated Access Control family controls. The findings demonstrate inadequate implementation of fundamental security principles including least privilege, access enforcement, account management, and remote access controls. The documented privilege escalation event and dormant credential reactivation represent active exploitation of these control failures.

Immediate remediation of critical findings is required to prevent further security incidents. The organization must prioritize implementation of the recommended corrective actions, with particular focus on revoking excessive privileges, enforcing MFA for remote access, and implementing automated compliance monitoring.

A follow-up assessment should be conducted within 90 days to verify remediation of critical and high-priority findings.

---

**Assessment Completed:** 2026-06-16  
**Assessor Signature:** [Digital Signature Required]  
**Next Assessment Due:** 2026-09-16