import { useEffect, useState, useCallback } from 'react';
import {
  Table,
  Card,
  Tag,
  Button,
  Modal,
  Input,
  Space,
  Select,
  message,
  Popconfirm,
} from 'antd';
import type { ColumnsType } from 'antd/es/table';
import { useNavigate } from 'react-router-dom';
import { devicesApi } from '../api/endpoints';
import type { Device } from '../types';

const { Search } = Input;

export default function DevicesPage() {
  const navigate = useNavigate();

  const [devices, setDevices] = useState<Device[]>([]);
  const [loading, setLoading] = useState(false);
  const [pagination, setPagination] = useState({
    current: 1,
    pageSize: 20,
    total: 0,
  });

  // Filters
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [searchText, setSearchText] = useState('');

  // Quarantine modal
  const [quarantineModalOpen, setQuarantineModalOpen] = useState(false);
  const [quarantineDeviceId, setQuarantineDeviceId] = useState<string | null>(null);
  const [quarantineReason, setQuarantineReason] = useState('');
  const [quarantineLoading, setQuarantineLoading] = useState(false);

  const fetchDevices = useCallback(
    async (page = 1, pageSize = 20) => {
      setLoading(true);
      try {
        const params: Record<string, unknown> = {
          page,
          page_size: pageSize,
        };
        if (statusFilter && statusFilter !== 'all') {
          params.status = statusFilter;
        }
        if (searchText) {
          params.search = searchText;
        }
        const response = await devicesApi.list(params);
        const body = response.data;
        // PaginatedResponse shape: { data: T[], pagination: {...} }
        if (body && Array.isArray(body.data)) {
          setDevices(body.data);
          setPagination({
            current: body.pagination?.page ?? page,
            pageSize: body.pagination?.page_size ?? pageSize,
            total: body.pagination?.total ?? 0,
          });
        } else if (Array.isArray(body)) {
          // Fallback if the API returns a plain array
          setDevices(body);
          setPagination({ current: page, pageSize, total: body.length });
        } else {
          setDevices([]);
          setPagination({ current: page, pageSize, total: 0 });
        }
      } catch (err: unknown) {
        const msg =
          err instanceof Error ? err.message : 'Failed to fetch devices';
        message.error(msg);
      } finally {
        setLoading(false);
      }
    },
    [statusFilter, searchText],
  );

  useEffect(() => {
    fetchDevices(1, pagination.pageSize);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Re-fetch when filters change
  useEffect(() => {
    fetchDevices(1, pagination.pageSize);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [statusFilter, searchText]);

  const handleTableChange = (pag: { current?: number; pageSize?: number }) => {
    fetchDevices(pag.current ?? 1, pag.pageSize ?? 20);
  };

  // ── Quarantine ──────────────────────────────────────────────────
  const openQuarantineModal = (deviceId: string) => {
    setQuarantineDeviceId(deviceId);
    setQuarantineReason('');
    setQuarantineModalOpen(true);
  };

  const handleQuarantine = async () => {
    if (!quarantineDeviceId || !quarantineReason.trim()) {
      message.warning('Please provide a reason for quarantine.');
      return;
    }
    setQuarantineLoading(true);
    try {
      await devicesApi.quarantine(quarantineDeviceId, quarantineReason.trim());
      message.success(`Device ${quarantineDeviceId} has been quarantined.`);
      setQuarantineModalOpen(false);
      setQuarantineDeviceId(null);
      setQuarantineReason('');
      fetchDevices(pagination.current, pagination.pageSize);
    } catch (err: unknown) {
      const msg =
        err instanceof Error ? err.message : 'Failed to quarantine device';
      message.error(msg);
    } finally {
      setQuarantineLoading(false);
    }
  };

  // ── Unquarantine ────────────────────────────────────────────────
  const handleUnquarantine = async (deviceId: string) => {
    try {
      await devicesApi.unquarantine(deviceId);
      message.success(`Device ${deviceId} has been unquarantined.`);
      fetchDevices(pagination.current, pagination.pageSize);
    } catch (err: unknown) {
      const msg =
        err instanceof Error ? err.message : 'Failed to unquarantine device';
      message.error(msg);
    }
  };

  // ── Status tag color ────────────────────────────────────────────
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

  const columns: ColumnsType<Device> = [
    {
      title: 'Device ID',
      dataIndex: 'device_id',
      key: 'device_id',
      ellipsis: true,
      width: 160,
    },
    {
      title: 'Hostname',
      dataIndex: 'hostname',
      key: 'hostname',
      ellipsis: true,
      width: 150,
    },
    {
      title: 'Username',
      dataIndex: 'username',
      key: 'username',
      width: 120,
    },
    {
      title: 'OS',
      dataIndex: 'os',
      key: 'os',
      width: 100,
    },
    {
      title: 'Status',
      dataIndex: 'status',
      key: 'status',
      width: 120,
      render: (_: unknown, record: Device) => statusTag(record.status),
    },
    {
      title: 'Quarantine',
      dataIndex: 'quarantine',
      key: 'quarantine',
      width: 110,
      render: (val: boolean) =>
        val ? <Tag color="red">Yes</Tag> : <Tag color="green">No</Tag>,
    },
    {
      title: 'Sessions',
      dataIndex: 'current_sessions',
      key: 'current_sessions',
      width: 90,
      align: 'center',
    },
    {
      title: 'Agent Runs',
      dataIndex: 'active_agent_runs',
      key: 'active_agent_runs',
      width: 110,
      align: 'center',
    },
    {
      title: 'Last Seen',
      dataIndex: 'last_seen_at',
      key: 'last_seen_at',
      width: 180,
      render: (val: string | null) =>
        val ? new Date(val).toLocaleString() : '—',
    },
    {
      title: 'Actions',
      key: 'actions',
      width: 300,
      fixed: 'right',
      render: (_: unknown, record: Device) => (
        <Space size="small">
          <Button
            type="link"
            size="small"
            onClick={() => navigate(`/devices/${record.device_id}`)}
          >
            View Detail
          </Button>
          {record.status !== 'quarantined' && (
            <Button
              type="link"
              size="small"
              danger
              onClick={() => openQuarantineModal(record.device_id)}
            >
              Quarantine
            </Button>
          )}
          {record.quarantine && (
            <Popconfirm
              title="Unquarantine device"
              description={`Remove quarantine from ${record.hostname}?`}
              onConfirm={() => handleUnquarantine(record.device_id)}
              okText="Yes"
              cancelText="No"
            >
              <Button type="link" size="small">
                Unquarantine
              </Button>
            </Popconfirm>
          )}
        </Space>
      ),
    },
  ];

  return (
    <div>
      <Card styles={{ body: { paddingBottom: 0 } }}>
        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            flexWrap: 'wrap',
            gap: 12,
            marginBottom: 16,
          }}
        >
          <h1 style={{ margin: 0, fontSize: 24 }}>Devices</h1>
          <Space wrap>
            <Select
              value={statusFilter}
              onChange={(val) => setStatusFilter(val)}
              style={{ width: 160 }}
              options={[
                { value: 'all', label: 'All Statuses' },
                { value: 'online', label: 'Online' },
                { value: 'offline', label: 'Offline' },
                { value: 'quarantined', label: 'Quarantined' },
              ]}
            />
            <Search
              placeholder="Search by hostname or username"
              allowClear
              style={{ width: 280 }}
              onSearch={(val) => setSearchText(val)}
              onChange={(e) => {
                if (!e.target.value) setSearchText('');
              }}
            />
          </Space>
        </div>
      </Card>

      <Card style={{ marginTop: 16 }}>
        <Table<Device>
          rowKey="device_id"
          columns={columns}
          dataSource={devices}
          loading={loading}
          scroll={{ x: 1400 }}
          pagination={{
            current: pagination.current,
            pageSize: pagination.pageSize,
            total: pagination.total,
            showSizeChanger: true,
            pageSizeOptions: ['10', '20', '50'],
            showTotal: (total) => `Total ${total} devices`,
          }}
          onChange={handleTableChange}
        />
      </Card>

      {/* Quarantine Modal */}
      <Modal
        title="Quarantine Device"
        open={quarantineModalOpen}
        onOk={handleQuarantine}
        onCancel={() => {
          setQuarantineModalOpen(false);
          setQuarantineDeviceId(null);
          setQuarantineReason('');
        }}
        confirmLoading={quarantineLoading}
        okText="Quarantine"
        okButtonProps={{ danger: true }}
      >
        <div style={{ marginBottom: 8 }}>
          <strong>Device:</strong> {quarantineDeviceId}
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
