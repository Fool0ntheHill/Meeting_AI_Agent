import { useEffect, useState } from 'react'
import { Card, Table, Typography, Alert } from 'antd'
import { listBills, type BillItem } from '@/api/billing'

const Billing = () => {
  const [data, setData] = useState<BillItem[]>([])
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    listBills()
      .then((res) => setData(res.items))
      .catch(() => {
        setError('后端不可用，使用静态账单示例')
        setData([
          { id: 'b1', amount: -12.5, type: 'consumption', created_at: '2024-01-01', remark: '转写' },
          { id: 'b2', amount: 100, type: 'recharge', created_at: '2024-01-02', remark: '充值' },
        ])
      })
  }, [])

  return (
    <div className="page-container">
      <Typography.Title level={4}>计费 / 账单</Typography.Title>
      {error && <Alert type="info" message={error} style={{ marginBottom: 12 }} />}
      <Card>
        <Table
          rowKey="id"
          dataSource={data}
          columns={[
            { title: '账单 ID', dataIndex: 'id' },
            { title: '类型', dataIndex: 'type', render: (v) => (v === 'recharge' ? '充值' : '消费') },
            { title: '金额', dataIndex: 'amount', render: (v) => `${v > 0 ? '+' : ''}${v} 元` },
            { title: '时间', dataIndex: 'created_at' },
            { title: '备注', dataIndex: 'remark' },
          ]}
        />
      </Card>
    </div>
  )
}

export default Billing
