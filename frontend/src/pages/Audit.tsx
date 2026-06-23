import React, { useState, useEffect } from 'react';
import {
  Table, Card, Tag, Select, Input, Space, Typography, Button, message,
  Descriptions, Row, Col, Statistic, Alert,
} from 'antd';
import { AuditOutlined, InfoCircleOutlined } from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import { dashboardApi } from '../api/endpoints';
import api from '../api/client';
import type { AuditLog, DashboardSummary, PaginatedResponse } from '../types';

const { Title, Text, Paragraph } = Typography;

const ACTION_OPTIONS = [
  { value: '', label: 'All Actions' },
  { value: 'login', label: 'Login' },
  { value: 'policy.publish', label: 'Policy Publish' },
  { value: 'device.quarantine', label: 'Device Quarantine' },
  { value: 'device.unquarantine', label: 'Device Unquarantine' },
  { value: 'approval.approve', label: 'Approval Approve' },
  { value: 'approval.deny', label: 'Approval Deny' },
  { value: 'device.enroll', label: 'Device Enroll' },
];

const TARGET_TYPE_OPTIONS = [
  { value: '', label: 'All Types' },
  { value: 'device', label: 'Device' },
  { value: 'policy', label: 'Policy' },
  { value: 'approval', label: 'Approval' },
  { value: 'user', label: 'User' },
];

const ACTION_COLOR: Record<string, string> = {
  login: 'blue',
  'policy.publish': 'purple',
  'device.quarantine': 'red',
  'device.unquarantine': 'green',
  'approval.approve': 'green',
  'approval.deny': 'red',
  'device.enroll': 'cyan',
};

function formatDateTime(iso: string | null): string {
  if (!iso) return '-';
  return new Date(iso).toLocaleString();
}

export default function AuditPage() {
  const [auditLogs, setAuditLogs] = useState<AuditLog[]>([]);
  const [loading, setLoading] = useState(false);
  const [summary, setSummary] = useState<DashboardSummary | null>(null);

  // Filters
  const [actorFilter, setActorFilter] = useState('');
  const [actionFilter, setActionFilter] = useState('');
  const [targetTypeFilter, setTargetTypeFilter] = useState('');

  // Pagination
  const [pagination, setPagination] = useState({ current: 1, pageSize: 10, total: 0 });

  // Expandable row state
  const [expandedKeys, setExpandedKeys] = useState<Set<string>>(new Set());

  useEffect(() => {
    // Load dashboard summary for stats
    dashboardApi.summary()
      .then((resp) => setSummary(resp.data as DashboardSummary))
      .catch(() => {
        // Summary endpoint may not be available yet
      });

    fetchAuditLogs();
  }, [actorFilter, actionFilter, targetTypeFilter, pagination.current, pagination.pageSize]);

  const fetchAuditLogs = async () => {
    setLoading(true);
    try {
      const params: Record<string, unknown> = {
        page: pagination.current,
        page_size: pagination.pageSize,
      };
      if (actorFilter) params.actor = actorFilter;
      if (actionFilter) params.action = actionFilter;
      if (targetTypeFilter) params.target_type = targetTypeFilter;

      // Attempt to call the audit endpoint; if it fails, show empty data gracefully
      try {
        const resp = await api.get('/api/v1/audit', { params });
        const data = resp.data as PaginatedResponse<AuditLog>;
        setAuditLogs(data.data);
        if (data.pagination) {
          setPagination(prev => ({
            ...prev,
            total: data.pagination.total ?? 0,
          }));
        }
      } catch {
        // Audit endpoint not available yet — show empty table with placeholder
        setAuditLogs([]);
        setPagination(prev => ({ ...prev, total: 0 }));
      }
    } finally {
      setLoading(false);
    }
  };

  const handleTableChange = (pag: { current?: number; pageSize?: number }) => {
    setPagination(prev => ({
      ...prev,
      current: pag.current ?? prev.current,
      pageSize: pag.pageSize ?? prev.pageSize,
    }));
  };

  const toggleExpand = (id: string) => {
    setExpandedKeys(prev => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  };

  const columns: ColumnsType<AuditLog> = [
    {
      title: 'Actor',
      dataIndex: 'actor',
      key: 'actor',
      width: 160,
      sorter: (a, b) => a.actor.localeCompare(b.actor),
      render: (actor: string) => (
        <Text strong style={{ fontFamily: 'monospace' }}>{actor}</Text>
      ),
    },
    {
      title: 'Action',
      dataIndex: 'action',
      key: 'action',
      width: 180,
      filters: ACTION_OPTIONS.filter(o => o.value !== '').map(o => ({ text: o.label, value: o.value })),
      onFilter: (value, record) => record.action === value,
      render: (action: string) => (
        <Tag color={ACTION_COLOR[action] || 'default'}>{action}</Tag>
      ),
    },
    {
      title: 'Target Type',
      dataIndex: 'target_type',
      key: 'target_type',
      width: 130,
      render: (type: string | null) => type ? <Tag>{type}</Tag> : <Text type="secondary">-</Text>,
    },
    {
      title: 'Target ID',
      dataIndex: 'target_id',
      key: 'target_id',
      width: 180,
      ellipsis: true,
      render: (id: string | null) => {
        if (!id) return <Text type="secondary">-</Text>;
        return <Text style={{ fontFamily: 'monospace', fontSize: 12 }}>{id}</Text>;
      },
    },
    {
      title: 'Detail',
      dataIndex: 'detail_json',
      key: 'detail_json',
      width: 100,
      render: (detail: Record<string, unknown> | null, record: AuditLog) => {
        if (!detail) return <Text type="secondary">-</Text>;
        const isExpanded = expandedKeys.has(record.id);
        return (
          <Button
            type="link"
            size="small"
            onClick={(e) => {
              e.stopPropagation();
              toggleExpand(record.id);
            }}
          >
            {isExpanded ? 'Collapse' : 'Expand'}
          </Button>
        );
      },
    },
    {
      title: 'Timestamp',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 180,
      sorter: (a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime(),
      defaultSortOrder: 'descend',
      render: (iso: string) => <Text>{formatDateTime(iso)}</Text>,
    },
  ];

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <Title level={3} style={{ margin: 0 }}>
          <AuditOutlined style={{ marginRight: 8 }} />
          Audit Log
        </Title>
      </div>

      {/* Info Alert — audit endpoint status */}
      <Alert
        message="Audit trail records all admin actions"
        description="Login attempts, policy changes, device quarantine/unquarantine, approval decisions, and device enrollments are tracked. Audit data is preserved for compliance and security review."
        type="info"
        showIcon
        icon={<InfoCircleOutlined />}
        style={{ marginBottom: 16 }}
      />

      {/* Summary Stats from Dashboard */}
      {summary && (
        <Row gutter={16} style={{ marginBottom: 16 }}>
          <Col span={4}>
            <Card size="small">
              <Statistic title="Online Devices" value={summary.online_devices} valueStyle={{ color: '#3f8600' }} />
            </Card>
          </Col>
          <Col span={4}>
            <Card size="small">
              <Statistic title="Quarantined" value={summary.quarantined_devices} valueStyle={{ color: '#cf1322' }} />
            </Card>
          </Col>
          <Col span={4}>
            <Card size="small">
              <Statistic title="Events (24h)" value={summary.total_events_24h} />
            </Card>
          </Col>
          <Col span={4}>
            <Card size="small">
              <Statistic title="Critical (24h)" value={summary.critical_events_24h} valueStyle={{ color: '#cf1322' }} />
            </Card>
          </Col>
          <Col span={4}>
            <Card size="small">
              <Statistic title="Pending Approvals" value={summary.pending_approvals} valueStyle={{ color: '#faad14' }} />
            </Card>
          </Col>
          <Col span={4}>
            <Card size="small">
              <Statistic title="Avg Risk (24h)" value={summary.avg_risk_score_24h} precision={1} />
            </Card>
          </Col>
        </Row>
      )}

      {/* Filter Bar */}
      <Card style={{ marginBottom: 16 }}>
        <Space wrap size="middle">
          <div>
            <Text strong style={{ marginRight: 8 }}>Actor:</Text>
            <Input
              placeholder="Search by username..."
              value={actorFilter}
              onChange={(e) => {
                setActorFilter(e.target.value);
                setPagination(prev => ({ ...prev, current: 1 }));
              }}
              allowClear
              style={{ width: 200 }}
            />
          </div>
          <div>
            <Text strong style={{ marginRight: 8 }}>Action:</Text>
            <Select
              value={actionFilter}
              onChange={(val) => {
                setActionFilter(val);
                setPagination(prev => ({ ...prev, current: 1 }));
              }}
              style={{ width: 180 }}
              options={ACTION_OPTIONS}
            />
          </div>
          <div>
            <Text strong style={{ marginRight: 8 }}>Target Type:</Text>
            <Select
              value={targetTypeFilter}
              onChange={(val) => {
                setTargetTypeFilter(val);
                setPagination(prev => ({ ...prev, current: 1 }));
              }}
              style={{ width: 140 }}
              options={TARGET_TYPE_OPTIONS}
            />
          </div>
        </Space>
      </Card>

      {/* Audit Table */}
      <Card>
        <Table<AuditLog>
          rowKey="id"
          columns={columns}
          dataSource={auditLogs}
          loading={loading}
          scroll={{ x: 1100 }}
          pagination={{
            current: pagination.current,
            pageSize: pagination.pageSize,
            total: pagination.total,
            showSizeChanger: true,
            showTotal: (total, range) => `${range[0]}-${range[1]} of ${total}`,
          }}
          onChange={handleTableChange}
          expandable={{
            expandedRowRender: (record: AuditLog) => {
              if (!record.detail_json) {
                return <Text type="secondary">No detail data available.</Text>;
              }
              return (
                <Card size="small" title="Detail JSON" style={{ marginLeft: 32, marginRight: 32 }}>
                  <pre style={{
                    background: '#f5f5f5',
                    padding: 16,
                    borderRadius: 8,
                    overflow: 'auto',
                    maxHeight: 400,
                    fontSize: 13,
                    fontFamily: 'monospace',
                    margin: 0,
                  }}>
                    {JSON.stringify(record.detail_json, null, 2)}
                  </pre>
                </Card>
              );
            },
            expandIcon: () => null, // Handled manually via the "Expand" button
            expandedRowKeys: Array.from(expandedKeys),
          }}
          locale={{
            emptyText: auditLogs.length === 0 && !loading
              ? (
                <div style={{ padding: 24 }}>
                  <Text type="secondary">
                    No audit logs found. Audit data will appear here once the audit endpoint is available
                    and admin actions are recorded.
                  </Text>
                </div>
              )
              : 'No audit logs found',
          }}
        />
      </Card>
    </div>
  );
}
