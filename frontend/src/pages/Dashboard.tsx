import React, { useState, useEffect } from 'react';
import { Card, Row, Col, Statistic, Table, Tag, Spin, Typography } from 'antd';
import {
  DesktopOutlined,
  WarningOutlined,
  ThunderboltOutlined,
  AlertOutlined,
  ClockCircleOutlined,
  RiseOutlined,
} from '@ant-design/icons';
import { dashboardApi } from '../api/endpoints';
import type {
  DashboardSummary,
  RiskTrendPoint,
  TopRiskyDevice,
  CriticalEvent,
} from '../types';

const { Title } = Typography;

// ── Helpers ────────────────────────────────────────────────────────

function severityColor(score: number): string {
  if (score >= 75) return 'red';
  if (score >= 50) return 'orange';
  if (score >= 25) return 'gold';
  return 'green';
}

function severityLabel(score: number): string {
  if (score >= 75) return 'Critical';
  if (score >= 50) return 'High';
  if (score >= 25) return 'Medium';
  return 'Low';
}

/** Axios wraps list responses in PaginatedResponse; unwrap if needed. */
function unwrapData<T>(payload: any): T[] {
  if (Array.isArray(payload)) return payload;
  if (payload && Array.isArray(payload.data)) return payload.data;
  return [];
}

// ── Risk Trend columns ─────────────────────────────────────────────

const riskTrendColumns = [
  { title: 'Hour', dataIndex: 'hour', key: 'hour', width: 160 },
  {
    title: 'Low',
    dataIndex: 'low',
    key: 'low',
    render: (v: number) => <Tag color="green">{v}</Tag>,
  },
  {
    title: 'Medium',
    dataIndex: 'medium',
    key: 'medium',
    render: (v: number) => <Tag color="gold">{v}</Tag>,
  },
  {
    title: 'High',
    dataIndex: 'high',
    key: 'high',
    render: (v: number) => <Tag color="orange">{v}</Tag>,
  },
  {
    title: 'Critical',
    dataIndex: 'critical',
    key: 'critical',
    render: (v: number) => <Tag color="red">{v}</Tag>,
  },
];

// ── Top Risky Devices columns ──────────────────────────────────────

const topRiskyColumns = [
  { title: 'Device ID', dataIndex: 'device_id', key: 'device_id', ellipsis: true },
  { title: 'Hostname', dataIndex: 'hostname', key: 'hostname' },
  { title: 'User', dataIndex: 'username', key: 'username' },
  {
    title: 'Avg Risk Score',
    dataIndex: 'avg_risk_score',
    key: 'avg_risk_score',
    sorter: (a: TopRiskyDevice, b: TopRiskyDevice) => a.avg_risk_score - b.avg_risk_score,
    render: (v: number) => (
      <Tag color={severityColor(v)}>{v.toFixed(1)}</Tag>
    ),
  },
  {
    title: 'Critical Count',
    dataIndex: 'critical_count',
    key: 'critical_count',
    render: (v: number) => (
      <Tag color={v > 0 ? 'red' : 'default'}>{v}</Tag>
    ),
  },
];

// ── Critical Events columns ────────────────────────────────────────

const criticalEventColumns = [
  { title: 'Event ID', dataIndex: 'event_id', key: 'event_id', ellipsis: true, width: 140 },
  { title: 'Device', dataIndex: 'hostname', key: 'hostname', width: 100 },
  { title: 'Tool', dataIndex: 'tool_name', key: 'tool_name', width: 100 },
  { title: 'Category', dataIndex: 'tool_category', key: 'tool_category', width: 100 },
  {
    title: 'Risk',
    dataIndex: 'risk_score',
    key: 'risk_score',
    width: 80,
    sorter: (a: CriticalEvent, b: CriticalEvent) => a.risk_score - b.risk_score,
    render: (v: number) => (
      <Tag color={severityColor(v)}>{severityLabel(v)}</Tag>
    ),
  },
  {
    title: 'Timestamp',
    dataIndex: 'timestamp',
    key: 'timestamp',
    width: 180,
    render: (v: string) => new Date(v).toLocaleString(),
  },
  { title: 'Reason', dataIndex: 'reason', key: 'reason', ellipsis: true },
];

// ── Dashboard Page ─────────────────────────────────────────────────

export default function DashboardPage() {
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [riskTrends, setRiskTrends] = useState<RiskTrendPoint[]>([]);
  const [topRiskyDevices, setTopRiskyDevices] = useState<TopRiskyDevice[]>([]);
  const [criticalEvents, setCriticalEvents] = useState<CriticalEvent[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;

    async function fetchAll() {
      setLoading(true);
      try {
        const [summaryRes, trendsRes, riskyRes, eventsRes] = await Promise.all([
          dashboardApi.summary(),
          dashboardApi.riskTrends(),
          dashboardApi.topRiskyDevices(),
          dashboardApi.recentCriticalEvents(),
        ]);

        if (cancelled) return;

        setSummary(summaryRes.data);
        setRiskTrends(unwrapData<RiskTrendPoint>(trendsRes.data));
        setTopRiskyDevices(unwrapData<TopRiskyDevice>(riskyRes.data));
        setCriticalEvents(unwrapData<CriticalEvent>(eventsRes.data));
      } catch (err) {
        if (!cancelled) {
          console.error('Failed to load dashboard data:', err);
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    fetchAll();

    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <Spin spinning={loading} size="large" tip="Loading dashboard...">
      <div style={{ padding: 24 }}>
        <Title level={3} style={{ marginBottom: 24 }}>
          Dashboard
        </Title>

        {/* ── Statistic Cards ──────────────────────────────────── */}
        <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
          <Col xs={24} sm={12} lg={8} xl={4}>
            <Card>
              <Statistic
                title="Online Devices"
                value={summary?.online_devices ?? 0}
                prefix={<DesktopOutlined />}
                valueStyle={{ color: '#52c41a' }}
              />
            </Card>
          </Col>
          <Col xs={24} sm={12} lg={8} xl={4}>
            <Card>
              <Statistic
                title="Quarantined"
                value={summary?.quarantined_devices ?? 0}
                prefix={<WarningOutlined />}
                valueStyle={{ color: '#faad14' }}
              />
            </Card>
          </Col>
          <Col xs={24} sm={12} lg={8} xl={4}>
            <Card>
              <Statistic
                title="Events (24h)"
                value={summary?.total_events_24h ?? 0}
                prefix={<ThunderboltOutlined />}
              />
            </Card>
          </Col>
          <Col xs={24} sm={12} lg={8} xl={4}>
            <Card>
              <Statistic
                title="Critical (24h)"
                value={summary?.critical_events_24h ?? 0}
                prefix={<AlertOutlined />}
                valueStyle={{ color: '#ff4d4f' }}
              />
            </Card>
          </Col>
          <Col xs={24} sm={12} lg={8} xl={4}>
            <Card>
              <Statistic
                title="Pending Approvals"
                value={summary?.pending_approvals ?? 0}
                prefix={<ClockCircleOutlined />}
                valueStyle={{ color: '#1677ff' }}
              />
            </Card>
          </Col>
          <Col xs={24} sm={12} lg={8} xl={4}>
            <Card>
              <Statistic
                title="Avg Risk Score"
                value={summary?.avg_risk_score_24h ?? 0}
                prefix={<RiseOutlined />}
                precision={1}
                valueStyle={{
                  color:
                    (summary?.avg_risk_score_24h ?? 0) >= 50
                      ? '#ff4d4f'
                      : '#52c41a',
                }}
              />
            </Card>
          </Col>
        </Row>

        {/* ── Risk Trend Table ────────────────────────────────── */}
        <Card
          title="Risk Trends (Last 24 Hours)"
          style={{ marginBottom: 24 }}
        >
          <Table
            dataSource={riskTrends}
            columns={riskTrendColumns}
            rowKey="hour"
            pagination={false}
            size="small"
            scroll={{ x: 600 }}
          />
        </Card>

        {/* ── Bottom Row: Top Risky Devices + Critical Events ──── */}
        <Row gutter={[16, 16]}>
          <Col xs={24} lg={12}>
            <Card title="Top Risky Devices">
              <Table
                dataSource={topRiskyDevices}
                columns={topRiskyColumns}
                rowKey="device_id"
                pagination={false}
                size="small"
                scroll={{ x: 500 }}
              />
            </Card>
          </Col>
          <Col xs={24} lg={12}>
            <Card title="Recent Critical Events">
              <Table
                dataSource={criticalEvents}
                columns={criticalEventColumns}
                rowKey="event_id"
                pagination={false}
                size="small"
                scroll={{ x: 700 }}
              />
            </Card>
          </Col>
        </Row>
      </div>
    </Spin>
  );
}
