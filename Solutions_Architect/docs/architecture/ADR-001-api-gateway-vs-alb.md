# ADR-001: API Gateway vs Application Load Balancer

## Status
Accepted

## Context
Need to choose the entry point for our SaaS API that handles authentication, rate limiting, and routing to backend services.

## Decision
Use AWS API Gateway instead of Application Load Balancer (ALB).

## Rationale

### API Gateway Advantages
- **Built-in Features**: Rate limiting, caching, request/response transformation
- **Security**: Integrated with Cognito, API keys, WAF
- **Serverless**: Auto-scaling from 0 to 10,000 RPS
- **Monitoring**: CloudWatch metrics, X-Ray tracing built-in
- **Cost Model**: Pay-per-request ($3.50/million requests)

### ALB Considerations
- **Lower Latency**: ~10ms vs ~50ms for API Gateway
- **WebSocket Support**: Native support vs API Gateway limitations
- **Cost**: Fixed monthly cost ($16) + per-LCU charges
- **Flexibility**: More routing options, custom headers

## Trade-offs

| Factor | API Gateway | ALB |
|--------|-------------|-----|
| Setup Complexity | Low | Medium |
| Built-in Security | High | Medium |
| Latency | 50-100ms | 10-20ms |
| Cost (low traffic) | Lower | Higher |
| Cost (high traffic) | Higher | Lower |
| WebSocket Support | Limited | Full |

## Decision Factors
1. **Rapid Development**: Built-in features reduce development time
2. **Security Requirements**: Need integrated rate limiting and authentication
3. **Traffic Patterns**: Expecting bursty, unpredictable traffic
4. **Team Expertise**: More familiar with API Gateway

## Consequences

### Positive
- Faster time to market
- Built-in security and monitoring
- Serverless scaling
- Integrated with AWS ecosystem

### Negative
- Higher latency than ALB
- Vendor lock-in to AWS
- Limited WebSocket support
- Higher costs at scale (>1M requests/month)

## Migration Path
If traffic exceeds 10M requests/month, consider hybrid approach:
- ALB for high-volume APIs
- API Gateway for admin/management APIs

## Review Date
Q2 2024 - Reassess based on traffic patterns and cost analysis