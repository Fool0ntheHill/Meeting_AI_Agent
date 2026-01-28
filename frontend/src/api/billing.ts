import { request } from './request'

export interface BillItem {
  id: string
  amount: number
  type: 'consumption' | 'recharge'
  created_at: string
  remark?: string
}

export const listBills = () =>
  request<{ items: BillItem[] }>({
    url: '/billing',
    method: 'GET',
  })
