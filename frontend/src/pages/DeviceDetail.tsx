import { useEffect, useState } from 'react';
import {
  Descriptions,
  Tabs,
  Table,
  Card,
  Tag,
  Button,
  Space,
  Typography,
  message,
  Modal,
  Input,
  Popconfirm,
} from 'antd';
import type { ColumnsType } from 'antd/es/table';
import { useParams, useNavigate } from 'react-router-dom';
import { devicesApi } from '../api/endpoints';
import type { Device, Event } from '../types';

const { Title } = Typography;

export default function DeviceDetailPage() {
  const { deviceId } = useParams<{ deviceId: string }>();
  const navigate = useNavigate();

  const [device, setDevice] = useState<Device | null>(null);
  const [loading, setLoading] = useState(true);

  const [events, setEvents] = useState<Event[]>([]);
  const [eventsLoading, setEventsLoading] = useState(false);

  const [policyYaml, setPolicyYaml] = useState<string | null>(null);
  const [policyLoading, setPolicyLoading] = useState(false);

  // Quarantine modal
  const [quarantineModalOpen, setQuarantineModalOpen] = useState(false);
  const [quarantineReason, setQuarantineReason] = useState('');
  const [quarantineLoading, setQuarantineLoading] = useState(false);

  // ── Fetch device ─────────────────────────────────────────────────
  const fetchDevice = async () => {
    if (!deviceId) return;
    setLoading(true);
    try {
      const response = await devicesApi.get(deviceId);
      setDevice(response.data);
    } catch (err: unknown) {
      const msg =
        err instanceof Error ? err.message : 'Failed to fetch device';
      message.error(msg);
    } finally {
      setLoading(false);
    }
  };

  // ── Fetch events ─────────────────────────────────────────────────
  const fetchEvents = async () => {
    if (!deviceId) return;
    setEventsLoading(true);
    try {
      const response = await devicesApi.getEvents(deviceId);
      const body = response.data;
      if (body && Array.isArray(body.data)) {
        setEvents(body.data);
      } else if (Array.isArray(body)) {
        setEvents(body);
      } else {
        setEvents([]);
      }
    } catch (err: unknown) {
      const msg =
        err instanceof Error ? err.message : 'Failed to fetch events';
      message.error(msg);
    } finally {
      setEventsLoading(false);
    }
  };

  // ── Fetch policy ─────────────────────────────────────────────────
  const fetchPolicy = async () => {
    if (!deviceId) return;
    setPolicyLoading(true);
    try {
      const response = await devicesApi.getPolicy(deviceId);
      setPolicyYaml(response.data.yaml_content ?? null);
    } catch (err: unknown) {
      // Policy may not exist for this device — that's ok
      setPolicyYaml(null);
    } finally {
      setPolicyLoading(false);
    }
  };

  useEffect(() => {
    fetchDevice();
  }, [deviceId]); // eslint-disable-line react-hooks/exhaustive-deps

  // ── Quarantine / Unquarantine ────────────────────────────────────
  const handleQuarantine = async () => {
    if (!deviceId || !quarantineReason.trim()) {
      message.warning('Please provide a reason for quarantine.');
      return;
    }
    setQuarantineLoading(true);
    try {
      await devicesApi.quarantine(deviceId, quarantineReason.trim());
      message.success(`Device ${deviceId} has been quarantined.`);
      setQuarantineModalOpen(false);
      setQuarantineReason('');
      fetchDevice();
    } catch (err: unknown) {
      const msg =
        err instanceof Error ? err.message : 'Failed to quarantine device';
      message.error(msg);
    } finally {
      setQuarantineLoading(false);
    }
  };

  const handleUnquarantine = async () => {
    if (!deviceId) return;
    try {
      await devicesApi.unquarantine(deviceId);
      message.success(`Device ${deviceId} has been unquarantined.`);
      fetchDevice();
    } catch (err: unknown) {
      const msg =
        err instanceof Error ? err.message : 'Failed to unquarantine device';
      message.error(msg);
    }
  };

  // ── Status tag ───────────────────────────────────────────────────
  const statusTag = (status: string) => {
    switch (status) {
      case 'online':
        return <Tag color="green">online</Tag>;
      case 'offline':
        return <Tag color="default">offline</Tag>;
      case 'quarantined':
        return <Tag color="red">quarantined</Tag>;
      default:
        return <Tag>{status}</Tag>;
    }
  };

  const severityTag = (severity: string | null) => {
    switch (severity) {
      case 'low':
        return <Tag color="blue">low</Tag>;
      case 'medium':
        return <Tag color="orange">medium</Tag>;
      case 'high':
        return <Tag color="volcano">high</Tag>;
      case 'critical':
        return <Tag color="red">critical</Tag>;
      default:
        return <Tag>—</Tag>;
    }
  };

  // ── Event table columns ──────────────────────────────────────────
  const eventColumns: ColumnsType<Event> = [
    {
      title: 'Event ID',
      dataIndex: 'event_id',
      key: 'event_id',
      width: 160,
      ellipsis: true,
    },
    {
      title: 'Event Type',
      dataIndex: 'event_type',
      key: 'event_type',
      width: 140,
    },
    {
      title: 'Tool',
      dataIndex: 'tool_name',
      key: 'tool_name',
      width: 120,
      render: (val: string | null) => val ?? '—',
    },
    {
      title: 'Risk Score',
      dataIndex: 'risk_score',
      key: 'risk_score',
      width: 100,
      align: 'center',
      sorter: (a, b) => a.risk_score - b.risk_score,
    },
    {
      title: 'Severity',
      dataIndex: 'severity',
      key: 'severity',
      width: 100,
      render: (_: unknown, record: Event) => severityTag(record.severity),
    },
    {
      title: 'Decision',
      dataIndex: 'policy_decision',
      key: 'policy_decision',
      width: 110,
      render: (val: string | null) =>
        val ? (
          <Tag color={val === 'allow' ? 'green' : val === 'deny' ? 'red' : 'default'}>
            {val}
          </Tag>
        ) : (
          '—'
        ),
    },
    {
      title: 'Timestamp',
      dataIndex: 'timestamp',
      key: 'timestamp',
      width: 180,
      render: (val: string) => new Date(val).toLocaleString(),
    },
  ];

  // ── Tab items ────────────────────────────────────────────────────
  const tabItems = [
    {
      key: 'events',
      label: 'Recent Events',
      children: (
        <Table<Event>
          rowKey="event_id"
          columns={eventColumns}
          dataSource={events}
          loading={eventsLoading}
          scroll={{ x: 900 }}
          pagination={{ pageSize: 20, showSizeChanger: true }}
        />
      ),
    },
    {
      key: 'policy',
      label: 'Policy',
      children: (
        <Card loading={policyLoading}>
          {policyYaml ? (
            <pre
              style={{
                background: '#f5f5f5',
                padding: 16,
                borderRadius: 8,
                overflow: 'auto',
                maxHeight: 600,
                fontSize: 13,
                lineHeight: 1.6,
              }}
            >
              <code>{policyYaml}</code>
            </pre>
          ) : (
            <div style={{ color: '#999' }}>
              No policy assigned to this device.
            </div>
          )}
        </Card>
      ),
    },
  ];

  if (!deviceId) {
    return (
      <Card>
        <Title level={4}>No device ID provided.</Title>
        <Button onClick={() => navigate('/devices')}>Back to Devices</Button>
      </Card>
    );
  }

  return (
    <div>
      {/* Header */}
      <Card styles={{ body: { paddingBottom: 12 } }}>
        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            flexWrap: 'wrap',
            gap: 12,
          }}
        >
          <Space>
            <Button onClick={() => navigate('/devices')}>← Back</Button>
            <Title level={3} style={{ margin: 0 }}>
              {device?.hostname ?? deviceId}
            </Title>
            {device && statusTag(device.status)}
            {device?.quarantine && (
              <Tag color="red">
                Quarantined
                {device.quarantine_reason
                  ? `: ${device.quarantine_reason}`
                  : ''}
              </Tag>
            )}
          </Space>

          <Space>
            {device && device.status !== 'quarantined' && (
              <Button
                danger
                onClick={() => {
                  setQuarantineReason('');
                  setQuarantineModalOpen(true);
                }}
              >
                Quarantine
              </Button>
            )}
            {device?.quarantine && (
              <Popconfirm
                title="Unquarantine device"
                description="Remove quarantine from this device?"
                onConfirm={handleUnquarantine}
                okText="Yes"
                cancelText="No"
              >
                <Button>Unquarantine</Button>
              </Popconfirm>
            )}
          </Space>
        </div>
      </Card>

      {/* Device Details */}
      <Card style={{ marginTop: 16 }} loading={loading}>
        <Descriptions
          bordered
          column={{ xs: 1, sm: 2, lg: 3 }}
          size="small"
        >
          <Descriptions.Item label="Device ID">
            {device?.device_id ?? '—'}
          </Descriptions.Item>
          <Descriptions.Item label="Hostname">
            {device?.hostname ?? '—'}
          </Descriptions.Item>
          <Descriptions.Item label="OS">
            {device?.os ?? '—'}
            {device?.os_version ? ` ${device.os_version}` : ''}
          </Descriptions.Item>
          <Descriptions.Item label="Username">
            {device?.username ?? '—'}
          </Descriptions.Item>
          <Descriptions.Item label="Status">
            {device ? statusTag(device.status) : '—'}
          </Descriptions.Item>
          <Descriptions.Item label="Quarantine">
            {device?.quarantine ? (
              <Tag color="red">Yes</Tag>
            ) : (
              <Tag color="green">No</Tag>
            )}
          </Descriptions.Item>
          <Descriptions.Item label="Quarantine Reason">
            {device?.quarantine_reason ?? '—'}
          </Descriptions.Item>
          <Descriptions.Item label="Quarantined At">
            {device?.quarantined_at
              ? new Date(device.quarantined_at).toLocaleString()
              : '—'}
          </Descriptions.Item>
          <Descriptions.Item label="OpenClaw Version">
            {device?.openclaw_version ?? '—'}
          </Descriptions.Item>
          <Descriptions.Item label="Plugin Version">
            {device?.plugin_version ?? '—'}
          </Descriptions.Item>
          <Descriptions.Item label="Sidecar Version">
            {device?.sidecar_version ?? '—'}
          </Descriptions.Item>
          <Descriptions.Item label="Policy ID">
            {device?.policy_id ?? '—'}
          </Descriptions.Item>
          <Descriptions.Item label="Policy Version">
            {device?.policy_version ?? '—'}
          </Descriptions.Item>
          <Descriptions.Item label="Current Sessions">
            {device?.current_sessions ?? 0}
          </Descriptions.Item>
          <Descriptions.Item label="Active Agent Runs">
            {device?.active_agent_runs ?? 0}
          </Descriptions.Item>
          <Descriptions.Item label="Last Seen">
            {device?.last_seen_at
              ? new Date(device.last_seen_at).toLocaleString()
              : '—'}
          </Descriptions.Item>
          <Descriptions.Item label="Created At">
            {device?.created_at
              ? new Date(device.created_at).toLocaleString()
              : '—'}
          </Descriptions.Item>
          <Descriptions.Item label="Updated At">
            {device?.updated_at
              ? new Date(device.updated_at).toLocaleString()
              : '—'}
          </Descriptions.Item>
        </Descriptions>
      </Card>

      {/* Tabs: Events + Policy */}
      <Card style={{ marginTop: 16 }}>
        <Tabs
          defaultActiveKey="events"
          items={tabItems}
          onTabClick={(key) => {
            if (key === 'events' && events.length === 0) fetchEvents();
            if (key === 'policy' && policyYaml === null) fetchPolicy();
          }}
        />
      </Card>

      {/* Quarantine Modal */}
      <Modal
        title="Quarantine Device"
        open={quarantineModalOpen}
        onOk={handleQuarantine}
        onCancel={() => {
          setQuarantineModalOpen(false);
          setQuarantineReason('');
        }}
        confirmLoading={quarantineLoading}
        okText="Quarantine"
        okButtonProps={{ danger: true }}
      >
        <div style={{ marginBottom: 8 }}>
          <strong>Device:</strong> {deviceId}
        </div>
        <Input.TextArea
          rows={3}
          placeholder="Enter reason for quarantine..."
          value={quarantineReason}
          onChange={(e) => setQuarantineReason(e.target.value)}
        />
      </Modal>
    </div>
  );
}
