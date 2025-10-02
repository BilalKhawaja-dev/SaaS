# Incident Response Playbook

## Quick Reference

### Emergency Contacts
- **Incident Commander**: +1-555-0101 (Primary), +1-555-0102 (Backup)
- **Technical Lead**: +1-555-0201 (Primary), +1-555-0202 (Backup)
- **Security Team**: security@company.com, +1-555-0301
- **Executive Escalation**: cto@company.com, +1-555-0401

### Critical System Access
- **AWS Console**: https://company.signin.aws.amazon.com/console
- **Status Page**: https://status.company.com/admin
- **Monitoring**: https://company.datadog.com
- **PagerDuty**: https://company.pagerduty.com

## Incident Classification & Response Times

| Severity | Description | Response Time | Escalation |
|----------|-------------|---------------|------------|
| **P0 - Critical** | Complete outage, security breach | 15 minutes | Immediate |
| **P1 - High** | Partial outage, major degradation | 1 hour | Within 30 min |
| **P2 - Medium** | Minor issues, <50% users affected | 4 hours | Within 2 hours |
| **P3 - Low** | Cosmetic issues, enhancement requests | 24 hours | Next business day |

## P0 - Critical Incident Response

### Immediate Actions (0-15 minutes)

#### 1. Incident Detection & Acknowledgment
```bash
# Acknowledge PagerDuty alert
# Join incident Slack channel: #incident-YYYY-MM-DD-HHMMSS
# Post initial status update
```

#### 2. Initial Assessment
- [ ] Confirm incident scope and impact
- [ ] Identify affected services/regions
- [ ] Estimate number of affected users
- [ ] Determine if security-related

#### 3. Incident Commander Actions
- [ ] Declare incident severity level
- [ ] Assemble incident response team
- [ ] Create incident war room (Zoom/Slack)
- [ ] Post initial status page update

### Status Page Update Template
```
🔴 INVESTIGATING: We are currently investigating reports of [service] being unavailable. 
We will provide updates as more information becomes available.

Posted: [timestamp]
Next update: [timestamp + 30 minutes]
```

### Team Assembly (5-10 minutes)
```
Required Roles:
├── Incident Commander: Overall coordination
├── Technical Lead: Technical investigation
├── Communications Lead: Customer updates
└── Customer Success: Customer liaison

Optional Roles (based on incident type):
├── Security Engineer: Security incidents
├── Database Administrator: Database issues
├── DevOps Engineer: Infrastructure issues
└── Product Manager: Business decisions
```

## Investigation Procedures

### System Health Checks
```bash
# 1. Check overall system status
aws cloudwatch get-metric-statistics \
  --namespace AWS/ApplicationELB \
  --metric-name TargetResponseTime \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 \
  --statistics Average

# 2. Check database connectivity
aws rds describe-db-clusters \
  --db-cluster-identifier production-cluster

# 3. Check ECS service status
aws ecs describe-services \
  --cluster production \
  --services api-service web-service

# 4. Check recent deployments
aws ecs list-tasks \
  --cluster production \
  --service-name api-service
```

### Log Analysis Commands
```bash
# Application logs (last 1 hour)
aws logs filter-log-events \
  --log-group-name /aws/ecs/api-service \
  --start-time $(date -d '1 hour ago' +%s)000 \
  --filter-pattern "ERROR"

# Database slow queries
aws logs filter-log-events \
  --log-group-name /aws/rds/instance/production/slowquery \
  --start-time $(date -d '1 hour ago' +%s)000

# Load balancer access logs
aws s3 cp s3://company-alb-logs/$(date +%Y/%m/%d)/ . --recursive
```

### Performance Metrics Check
```bash
# API response times
aws cloudwatch get-metric-statistics \
  --namespace AWS/ApplicationELB \
  --metric-name TargetResponseTime \
  --dimensions Name=LoadBalancer,Value=app/production-alb/1234567890 \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 \
  --statistics Average,Maximum

# Database connections
aws cloudwatch get-metric-statistics \
  --namespace AWS/RDS \
  --metric-name DatabaseConnections \
  --dimensions Name=DBClusterIdentifier,Value=production-cluster \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 \
  --statistics Average,Maximum
```

## Common Incident Scenarios

### Database Connection Issues

#### Symptoms
- High response times (>5 seconds)
- Connection timeout errors
- 500 errors in application logs

#### Investigation Steps
```bash
# 1. Check database status
aws rds describe-db-clusters --db-cluster-identifier production-cluster

# 2. Check connection count
aws cloudwatch get-metric-statistics \
  --namespace AWS/RDS \
  --metric-name DatabaseConnections \
  --dimensions Name=DBClusterIdentifier,Value=production-cluster

# 3. Check for long-running queries
# Connect to database and run:
# SELECT * FROM information_schema.processlist WHERE time > 30;

# 4. Check application connection pool
kubectl logs -l app=api-service --tail=100 | grep -i "connection"
```

#### Resolution Steps
1. **Immediate**: Scale up database instance if CPU/memory high
2. **Short-term**: Kill long-running queries if identified
3. **Medium-term**: Optimize problematic queries
4. **Long-term**: Implement connection pooling improvements

### High Traffic / DDoS Attack

#### Symptoms
- Sudden spike in traffic (>10x normal)
- High response times
- Rate limiting triggers

#### Investigation Steps
```bash
# 1. Check traffic patterns
aws cloudwatch get-metric-statistics \
  --namespace AWS/ApplicationELB \
  --metric-name RequestCount \
  --dimensions Name=LoadBalancer,Value=app/production-alb/1234567890

# 2. Check WAF blocked requests
aws wafv2 get-sampled-requests \
  --web-acl-arn arn:aws:wafv2:us-east-1:123456789012:global/webacl/production/12345678

# 3. Analyze source IPs
aws s3 cp s3://company-alb-logs/$(date +%Y/%m/%d)/ . --recursive
cat *.log | awk '{print $3}' | sort | uniq -c | sort -nr | head -20
```

#### Resolution Steps
1. **Immediate**: Enable AWS Shield Advanced if not already active
2. **Short-term**: Add WAF rules to block malicious IPs
3. **Medium-term**: Scale up infrastructure capacity
4. **Long-term**: Implement advanced DDoS protection

### Application Deployment Issues

#### Symptoms
- Errors started after recent deployment
- New version showing errors
- Rollback needed

#### Investigation Steps
```bash
# 1. Check recent deployments
aws ecs describe-services --cluster production --services api-service

# 2. Check task health
aws ecs list-tasks --cluster production --service-name api-service
aws ecs describe-tasks --cluster production --tasks [task-arn]

# 3. Check application logs for new errors
aws logs filter-log-events \
  --log-group-name /aws/ecs/api-service \
  --start-time $(date -d '30 minutes ago' +%s)000 \
  --filter-pattern "ERROR"
```

#### Resolution Steps
1. **Immediate**: Rollback to previous version
2. **Short-term**: Investigate root cause in staging
3. **Medium-term**: Fix issues and redeploy
4. **Long-term**: Improve deployment testing

## Escalation Procedures

### When to Escalate
- Incident duration >30 minutes without progress
- Customer impact >1000 users
- Security breach suspected
- Data loss potential identified
- Media attention likely

### Escalation Chain
```
Level 1: On-call Engineer
    ↓ (30 minutes)
Level 2: Team Lead
    ↓ (1 hour)
Level 3: Engineering Manager
    ↓ (2 hours)
Level 4: CTO
    ↓ (4 hours)
Level 5: CEO
```

### Executive Notification Template
```
Subject: P0 Incident - [Brief Description]

Executive Summary:
- Incident: [Description]
- Impact: [Number of users affected]
- Duration: [Time since start]
- ETA to Resolution: [Estimate]
- Customer Communication: [Status page updated]
- Next Update: [Time]

Technical Details:
- Root Cause: [If known]
- Resolution Steps: [Current actions]
- Team Assigned: [Names and roles]

Business Impact:
- Revenue Impact: [Estimate]
- SLA Impact: [Affected customers]
- Reputation Risk: [Assessment]
```

## Communication Templates

### Initial Customer Communication
```
Subject: Service Disruption - [Service Name]

We are currently experiencing issues with [service name] that may affect your ability to [specific impact]. 

Our engineering team is actively investigating and working to resolve this issue as quickly as possible.

We will provide updates every 30 minutes until resolved.

Status page: https://status.company.com
Next update: [Time]

We apologize for any inconvenience.
```

### Resolution Communication
```
Subject: Service Restored - [Service Name]

The issue affecting [service name] has been resolved as of [time].

Root Cause: [Brief explanation]
Resolution: [What was done]
Prevention: [Steps to prevent recurrence]

If you continue to experience issues, please contact support at support@company.com.

We apologize for the disruption and appreciate your patience.
```

### Post-Incident Summary
```
Subject: Post-Incident Summary - [Date]

Incident Summary:
- Duration: [Start time] to [End time] ([Total duration])
- Impact: [Number of users, services affected]
- Root Cause: [Detailed explanation]

Timeline:
- [Time]: Issue detected
- [Time]: Investigation started
- [Time]: Root cause identified
- [Time]: Fix implemented
- [Time]: Service restored

Lessons Learned:
- [Key findings]
- [Process improvements]
- [Technical improvements]

Action Items:
- [Specific tasks with owners and due dates]
```

## Post-Incident Procedures

### Immediate Post-Incident (0-2 hours)
- [ ] Confirm all systems are stable
- [ ] Send resolution communication
- [ ] Update status page to "All Systems Operational"
- [ ] Document timeline and actions taken
- [ ] Schedule post-incident review meeting

### Post-Incident Review (24-48 hours)
- [ ] Conduct blameless post-mortem
- [ ] Document root cause analysis
- [ ] Identify action items for prevention
- [ ] Update runbooks and procedures
- [ ] Share learnings with broader team

### Follow-up Actions (1-2 weeks)
- [ ] Implement preventive measures
- [ ] Update monitoring and alerting
- [ ] Conduct additional testing
- [ ] Review and update incident response procedures
- [ ] Training updates if needed

## Monitoring & Alerting

### Critical Alerts
```yaml
Database Alerts:
  - Connection count >80% of max
  - Query response time >1 second
  - Replication lag >30 seconds
  - CPU utilization >80%

Application Alerts:
  - Error rate >1%
  - Response time >2 seconds P95
  - Memory utilization >85%
  - Disk space >90%

Infrastructure Alerts:
  - Load balancer 5xx errors >10/minute
  - Auto-scaling events
  - Security group changes
  - Failed health checks
```

### Alert Fatigue Prevention
- Regular alert tuning (monthly)
- Escalation policies based on severity
- Alert correlation to reduce noise
- Automated remediation where possible

## Tools & Resources

### Essential Tools
- **PagerDuty**: Incident alerting and escalation
- **Slack**: Team communication (#incident-response)
- **Datadog**: Monitoring and metrics
- **AWS Console**: Infrastructure management
- **Status Page**: Customer communication

### Useful Commands Cheat Sheet
```bash
# Quick system overview
aws cloudwatch get-metric-statistics --namespace AWS/ApplicationELB --metric-name RequestCount
aws ecs describe-services --cluster production
aws rds describe-db-clusters

# Log analysis
aws logs filter-log-events --log-group-name /aws/ecs/api-service --filter-pattern "ERROR"

# Traffic analysis
aws wafv2 get-sampled-requests --web-acl-arn [arn]

# Database queries
mysql -h [endpoint] -u [user] -p -e "SHOW PROCESSLIST;"
```

### Emergency Procedures Quick Access
- Database failover: `/playbooks/database-failover.md`
- Application rollback: `/playbooks/application-rollback.md`
- Security incident: `/playbooks/security-incident.md`
- DDoS response: `/playbooks/ddos-response.md`