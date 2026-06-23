import React, { useState, useEffect, useCallback } from 'react';
import {
  Table, Card, Tag, Select, Button, Drawer, Modal, Space, Typography,
  Tooltip, message, Descriptions, Input, Checkbox, Badge,
} from 'antd';
import { CheckCircleOutlined, CloseCircleOutlined, ExclamationCircleOutlined, ClockCircleOutlined } from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import { approvalsApi } from '../api/endpoints';
import type { Approval, PaginatedResponse } from '../types';

const { Title, Text, Paragraph } = Typography;
const { TextArea } = Input;

const STATUS_OPTIONS = [
  { value: '', label: 'All' },
  { value: 'pending', label: 'Pending' },
  { value: 'approved', label: 'Approved' },
  { value: 'denied', label: 'Denied' },
  { value: 'expired', label: 'Expired' },
];

const STATUS_COLOR: Record<string, string> = {
  pending: 'processing',
  approved: 'success',
  denied: 'error',
  expired: 'default',
};

function getRiskColor(score: number | null): string {
  if (score === null) return 'default';
  if (score >= 80) return 'red';
  if (score >= 60) return 'orange';
  if (score >= 40) return 'gold';
  return 'green';
}

function getRiskLabel(score: number | null): string {
  if (score === null) return 'N/A';
  if (score >= 80) return 'Critical';
  if (score >= 60) return 'High';
  if (score >= 40) return 'Medium';
  return 'Low';
}

function truncateText(text: string | null, maxLen = 60): string {
  if (!text) return '-';
  return text.length > maxLen ? text.slice(0, maxLen) + '...' : text;
}

function formatDateTime(iso: string | null): string {
  if (!iso) return '-';
  return new Date(iso).toLocaleString();
}

export default function ApprovalsPage() {
  const [approvals, setApprovals] = useState<Approval[]>([]);
  const [loading, setLoading] = useState(false);
  const [statusFilter, setStatusFilter] = useState<string>('pending');
  const [pagination, setPagination] = useState({ current: 1, pageSize: 10, total: 0 });

  // Detail drawer
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [selectedApproval, setSelectedApproval] = useState<Approval | null>(null);

  // Approve modal
  const [approveModalOpen, setApproveModalOpen] = useState(false);
  const [approveTarget, setApproveTarget] = useState<Approval | null>(null);
  const [approveReason, setApproveReason] = useState('');
  const [approving, setApproving] = useState(false);

  // Deny modal
  const [denyModalOpen, setDenyModalOpen] = useState(false);
  const [denyTarget, setDenyTarget] = useState<Approval | null>(null);
  const [denyReason, setDenyReason] = useState('');
  const [quarantineDevice, setQuarantineDevice] = useState(false);
  const [denying, setDenying] = useState(false);

  const fetchApprovals = useCallback(async () => {
    setLoading(true);
    try {
      const params: Record<string, unknown> = {
        page: pagination.current,
        page_size: pagination.pageSize,
      };
      if (statusFilter) {
        params.status = statusFilter;
      }
      const resp = await approvalsApi.list(params);
      const data = resp.data as PaginatedResponse<Approval>;
      setApprovals(data.data);
      if (data.pagination) {
        setPagination(prev => ({
          ...prev,
          total: data.pagination.total ?? 0,
        }));
      }
    } catch (err: any) {
      const detail = err?.response?.data?.detail || err?.response?.data?.message || 'Failed to load approvals';
      message.error(detail);
    } finally {
      setLoading(false);
    }
  }, [statusFilter, pagination.current, pagination.pageSize]);

  useEffect(() => {
    fetchApprovals();
  }, [fetchApprovals]);

  // Auto-refresh every 10 seconds
  useEffect(() => {
    const interval = setInterval(() => {
      fetchApprovals();
    }, 10_000);
    return () => clearInterval(interval);
  }, [fetchApprovals]);

  const handleTableChange = (pag: { current?: number; pageSize?: number }) => {
    setPagination(prev => ({
      ...prev,
      current: pag.current ?? prev.current,
      pageSize: pag.pageSize ?? prev.pageSize,
    }));
  };

  const openDrawer = (record: Approval) => {
    setSelectedApproval(record);
    setDrawerOpen(true);
  };

  const handleApprove = async () => {
    if (!approveTarget) return;
    setApproving(true);
    try {
      await approvalsApi.approve(approveTarget.approval_id, approveReason || undefined);
      message.success(`Approval ${approveTarget.approval_id} approved`);
      setApproveModalOpen(false);
      setApproveTarget(null);
      setApproveReason('');
      fetchApprovals();
    } catch (err: any) {
      const detail = err?.response?.data?.detail || err?.response?.data?.message || 'Failed to approve';
      message.error(detail);
    } finally {
      setApproving(false);
    }
  };

  const handleDeny = async () => {
    if (!denyTarget) return;
    setDenying(true);
    try {
      await approvalsApi.deny(denyTarget.approval_id, denyReason || undefined, quarantineDevice);
      message.success(`Approval ${denyTarget.approval_id} denied`);
      setDenyModalOpen(false);
      setDenyTarget(null);
      setDenyReason('');
      setQuarantineDevice(false);
      fetchApprovals();
    } catch (err: any) {
      const detail = err?.response?.data?.detail || err?.response?.data?.message || 'Failed to deny';
      message.error(detail);
    } finally {
      setDenying(false);
    }
  };

  // Countdown renderer for pending approvals
  const renderExpiresAt = (expiresAt: string, status: string) => {
    if (status !== 'pending') {
      return <Text type="secondary">{formatDateTime(expiresAt)}</Text>;
    }
    const diff = new Date(expiresAt).getTime() - Date.now();
    if (diff <= 0) {
      return <Badge status="error" text="Expired" />;
    }
    const minutes = Math.floor(diff / 60000);
    const seconds = Math.floor((diff % 60000) / 1000);
    const display = `${minutes}m ${seconds}s`;
    return (
      <Tooltip title={formatDateTime(expiresAt)}>
        <Text type={minutes < 2 ? 'danger' : 'warning'}>{display}</Text>
      </Tooltip>
    );
  };

  const columns: ColumnsType<Approval> = [
    {
      title: 'Approval ID',
      dataIndex: 'approval_id',
      key: 'approval_id',
      width: 180,
      ellipsis: true,
      render: (id: string) => (
        <Text copyable style={{ fontFamily: 'monospace', fontSize: 12 }}>{id}</Text>
      ),
    },
    {
      title: 'Device ID',
      dataIndex: 'device_id',
      key: 'device_id',
      width: 160,
      ellipsis: true,
      render: (id: string) => (
        <Text style={{ fontFamily: 'monospace', fontSize: 12 }}>{id}</Text>
      ),
    },
    {
      title: 'Tool',
      dataIndex: 'tool_name',
      key: 'tool_name',
      width: 140,
      render: (name: string | null) => name || '-',
    },
    {
      title: 'Params Summary',
      dataIndex: 'params_summary',
      key: 'params_summary',
      width: 220,
      render: (text: string | null) => {
        if (!text) return <Text type="secondary">-</Text>;
        return (
          <Tooltip title={text} placement="topLeft">
            <Text style={{ fontSize: 12 }}>{truncateText(text, 60)}</Text>
          </Tooltip>
        );
      },
    },
    {
      title: 'Risk Score',
      dataIndex: 'risk_score',
      key: 'risk_score',
      width: 100,
      sorter: (a, b) => (a.risk_score ?? 0) - (b.risk_score ?? 0),
      render: (score: number | null) => (
        <Tag color={getRiskColor(score)}>{getRiskLabel(score)} ({score ?? 'N/A'})</Tag>
      ),
    },
    {
      title: 'Reason',
      dataIndex: 'reason',
      key: 'reason',
      width: 180,
      ellipsis: true,
      render: (text: string | null) => {
        if (!text) return <Text type="secondary">-</Text>;
        return (
          <Tooltip title={text} placement="topLeft">
            <Text>{text}</Text>
          </Tooltip>
        );
      },
    },
    {
      title: 'Status',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      filters: STATUS_OPTIONS.filter(o => o.value !== '').map(o => ({ text: o.label, value: o.value })),
      onFilter: (value, record) => record.status === value,
      render: (status: string) => <Tag color={STATUS_COLOR[status]}>{status.toUpperCase()}</Tag>,
    },
    {
      title: 'Requested At',
      dataIndex: 'requested_at',
      key: 'requested_at',
      width: 170,
      sorter: (a, b) => new Date(a.requested_at).getTime() - new Date(b.requested_at).getTime(),
      defaultSortOrder: 'descend',
      render: (iso: string) => <Text>{formatDateTime(iso)}</Text>,
    },
    {
      title: 'Expires At',
      dataIndex: 'expires_at',
      key: 'expires_at',
      width: 120,
      render: (expiresAt: string, record: Approval) => renderExpiresAt(expiresAt, record.status),
    },
    {
      title: 'Decided By',
      dataIndex: 'decided_by',
      key: 'decided_by',
      width: 130,
      render: (text: string | null) => text || <Text type="secondary">-</Text>,
    },
    {
      title: 'Actions',
      key: 'actions',
      width: 160,
      fixed: 'right',
      render: (_: unknown, record: Approval) => {
        if (record.status !== 'pending') {
          return <Text type="secondary">-</Text>;
        }
        return (
          <Space size="small">
            <Button
              type="primary"
              size="small"
              icon={<CheckCircleOutlined />}
              style={{ backgroundColor: '#52c41a', borderColor: '#52c41a' }}
              onClick={(e) => {
                e.stopPropagation();
                setApproveTarget(record);
                setApproveReason('');
                setApproveModalOpen(true);
              }}
            >
              Approve
            </Button>
            <Button
              danger
              size="small"
              icon={<CloseCircleOutlined />}
              onClick={(e) => {
                e.stopPropagation();
                setDenyTarget(record);
                setDenyReason('');
                setQuarantineDevice(false);
                setDenyModalOpen(true);
              }}
            >
              Deny
            </Button>
          </Space>
        );
      },
    },
  ];

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <Title level={3} style={{ margin: 0 }}>Approvals</Title>
        <Select
          value={statusFilter}
          onChange={(val) => {
            setStatusFilter(val);
            setPagination(prev => ({ ...prev, current: 1 }));
          }}
          style={{ width: 140 }}
          options={STATUS_OPTIONS}
        />
      </div>

      <Card>
        <Table<Approval>
          rowKey="id"
          columns={columns}
          dataSource={approvals}
          loading={loading}
          scroll={{ x: 1500 }}
          pagination={{
            current: pagination.current,
            pageSize: pagination.pageSize,
            total: pagination.total,
            showSizeChanger: true,
            showTotal: (total, range) => `${range[0]}-${range[1]} of ${total}`,
          }}
          onChange={handleTableChange}
          onRow={(record) => ({
            onClick: () => openDrawer(record),
            style: { cursor: 'pointer' },
          })}
          locale={{ emptyText: 'No approvals found' }}
        />
      </Card>

      {/* Detail Drawer */}
      <Drawer
        title={selectedApproval ? `Approval: ${selectedApproval.approval_id}` : 'Approval Detail'}
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        width={560}
      >
        {selectedApproval && (
          <Space direction="vertical" size="middle" style={{ width: '100%' }}>
            <Descriptions column={1} bordered size="small">
              <Descriptions.Item label="Approval ID">
                <Text copyable style={{ fontFamily: 'monospace' }}>{selectedApproval.approval_id}</Text>
              </Descriptions.Item>
              <Descriptions.Item label="Device ID">
                <Text style={{ fontFamily: 'monospace' }}>{selectedApproval.device_id}</Text>
              </Descriptions.Item>
              <Descriptions.Item label="Event ID">
                {selectedApproval.event_id || <Text type="secondary">-</Text>}
              </Descriptions.Item>
              <Descriptions.Item label="Tool Name">
                {selectedApproval.tool_name || <Text type="secondary">-</Text>}
              </Descriptions.Item>
              <Descriptions.Item label="Session ID">
                {selectedApproval.session_id || <Text type="secondary">-</Text>}
              </Descriptions.Item>
              <Descriptions.Item label="Run ID">
                {selectedApproval.run_id || <Text type="secondary">-</Text>}
              </Descriptions.Item>
              <Descriptions.Item label="Risk Score">
                <Tag color={getRiskColor(selectedApproval.risk_score)}>
                  {getRiskLabel(selectedApproval.risk_score)} ({selectedApproval.risk_score ?? 'N/A'})
                </Tag>
              </Descriptions.Item>
              <Descriptions.Item label="Status">
                <Tag color={STATUS_COLOR[selectedApproval.status]}>{selectedApproval.status.toUpperCase()}</Tag>
              </Descriptions.Item>
              <Descriptions.Item label="Requested At">
                {formatDateTime(selectedApproval.requested_at)}
              </Descriptions.Item>
              <Descriptions.Item label="Expires At">
                {formatDateTime(selectedApproval.expires_at)}
              </Descriptions.Item>
              <Descriptions.Item label="Decided By">
                {selectedApproval.decided_by || <Text type="secondary">-</Text>}
              </Descriptions.Item>
              <Descriptions.Item label="Decided At">
                {selectedApproval.decided_at ? formatDateTime(selectedApproval.decided_at) : <Text type="secondary">-</Text>}
              </Descriptions.Item>
              <Descriptions.Item label="Decision Reason">
                {selectedApproval.decision_reason || <Text type="secondary">-</Text>}
              </Descriptions.Item>
            </Descriptions>

            {selectedApproval.params_summary && (
              <Card title="Params Summary" size="small">
                <Paragraph style={{ whiteSpace: 'pre-wrap', margin: 0, fontSize: 13 }}>
                  {selectedApproval.params_summary}
                </Paragraph>
              </Card>
            )}

            {selectedApproval.reason && (
              <Card title="Reason" size="small">
                <Paragraph style={{ margin: 0 }}>{selectedApproval.reason}</Paragraph>
              </Card>
            )}

            {selectedApproval.risk_labels_json && selectedApproval.risk_labels_json.length > 0 && (
              <Card title="Risk Labels" size="small">
                <Space wrap>
                  {selectedApproval.risk_labels_json.map((label, idx) => (
                    <Tag key={idx} color="volcano">{label}</Tag>
                  ))}
                </Space>
              </Card>
            )}
          </Space>
        )}
      </Drawer>

      {/* Approve Modal */}
      <Modal
        title={
          <Space>
            <CheckCircleOutlined style={{ color: '#52c41a' }} />
            Approve Request
          </Space>
        }
        open={approveModalOpen}
        onOk={handleApprove}
        onCancel={() => {
          setApproveModalOpen(false);
          setApproveTarget(null);
          setApproveReason('');
        }}
        confirmLoading={approving}
        okText="Approve"
        okButtonProps={{ style: { backgroundColor: '#52c41a', borderColor: '#52c41a' } }}
      >
        {approveTarget && (
          <Space direction="vertical" style={{ width: '100%' }} size="middle">
            <Descriptions column={1} size="small" bordered>
              <Descriptions.Item label="Approval ID">
                {approveTarget.approval_id}
              </Descriptions.Item>
              <Descriptions.Item label="Device">
                {approveTarget.device_id}
              </Descriptions.Item>
              <Descriptions.Item label="Tool">
                {approveTarget.tool_name || '-'}
              </Descriptions.Item>
              <Descriptions.Item label="Risk Score">
                <Tag color={getRiskColor(approveTarget.risk_score)}>
                  {approveTarget.risk_score ?? 'N/A'}
                </Tag>
              </Descriptions.Item>
            </Descriptions>
            <div>
              <Text strong>Justification / Reason (optional):</Text>
              <TextArea
                rows={3}
                value={approveReason}
                onChange={(e) => setApproveReason(e.target.value)}
                placeholder="Why are you approving this tool call?"
                style={{ marginTop: 8 }}
              />
            </div>
          </Space>
        )}
      </Modal>

      {/* Deny Modal */}
      <Modal
        title={
          <Space>
            <CloseCircleOutlined style={{ color: '#ff4d4f' }} />
            Deny Request
          </Space>
        }
        open={denyModalOpen}
        onOk={handleDeny}
        onCancel={() => {
          setDenyModalOpen(false);
          setDenyTarget(null);
          setDenyReason('');
          setQuarantineDevice(false);
        }}
        confirmLoading={denying}
        okText="Deny"
        okButtonProps={{ danger: true }}
      >
        {denyTarget && (
          <Space direction="vertical" style={{ width: '100%' }} size="middle">
            <Descriptions column={1} size="small" bordered>
              <Descriptions.Item label="Approval ID">
                {denyTarget.approval_id}
              </Descriptions.Item>
              <Descriptions.Item label="Device">
                {denyTarget.device_id}
              </Descriptions.Item>
              <Descriptions.Item label="Tool">
                {denyTarget.tool_name || '-'}
              </Descriptions.Item>
              <Descriptions.Item label="Risk Score">
                <Tag color={getRiskColor(denyTarget.risk_score)}>
                  {denyTarget.risk_score ?? 'N/A'}
                </Tag>
              </Descriptions.Item>
            </Descriptions>
            <div>
              <Text strong>Reason for denial (required):</Text>
              <TextArea
                rows={3}
                value={denyReason}
                onChange={(e) => setDenyReason(e.target.value)}
                placeholder="Why are you denying this tool call?"
                style={{ marginTop: 8 }}
              />
            </div>
            <Checkbox
              checked={quarantineDevice}
              onChange={(e) => setQuarantineDevice(e.target.checked)}
            >
              <Space>
                <ExclamationCircleOutlined style={{ color: '#faad14' }} />
                <Text>Quarantine Device — isolate the device after denial</Text>
              </Space>
            </Checkbox>
          </Space>
        )}
      </Modal>
    </div>
  );
}
