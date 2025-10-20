import React from 'react';
import { useQuery } from 'react-query';
import { Link } from 'react-router-dom';
import { receiptAPI } from '../api/client';
import { 
  DocumentTextIcon, 
  ClockIcon, 
  CheckCircleIcon, 
  XCircleIcon 
} from '@heroicons/react/24/outline';

export default function Dashboard() {
  const { data: receiptsData } = useQuery('recent-receipts', () => 
    receiptAPI.list({ page: 1, page_size: 5 })
  );

  const receipts = receiptsData?.data?.receipts || [];
  const total = receiptsData?.data?.total || 0;

  const stats = [
    {
      name: 'Total Receipts',
      value: total,
      icon: DocumentTextIcon,
      color: 'bg-blue-500'
    },
    {
      name: 'Processing',
      value: receipts.filter(r => r.processing_status === 'processing').length,
      icon: ClockIcon,
      color: 'bg-yellow-500'
    },
    {
      name: 'Completed',
      value: receipts.filter(r => r.processing_status === 'done').length,
      icon: CheckCircleIcon,
      color: 'bg-green-500'
    },
    {
      name: 'Errors',
      value: receipts.filter(r => r.processing_status === 'error').length,
      icon: XCircleIcon,
      color: 'bg-red-500'
    },
  ];

  return (
    <div className="px-4 sm:px-0">
      <h1 className="text-2xl font-semibold text-gray-900 mb-6">Dashboard</h1>

      {/* Stats */}
      <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-4 mb-8">
        {stats.map((stat) => (
          <div key={stat.name} className="bg-white overflow-hidden shadow rounded-lg">
            <div className="p-5">
              <div className="flex items-center">
                <div className={`flex-shrink-0 rounded-md p-3 ${stat.color}`}>
                  <stat.icon className="h-6 w-6 text-white" />
                </div>
                <div className="ml-5 w-0 flex-1">
                  <dl>
                    <dt className="text-sm font-medium text-gray-500 truncate">
                      {stat.name}
                    </dt>
                    <dd className="text-2xl font-semibold text-gray-900">
                      {stat.value}
                    </dd>
                  </dl>
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Recent receipts */}
      <div className="bg-white shadow rounded-lg">
        <div className="px-4 py-5 sm:px-6 border-b border-gray-200 flex justify-between items-center">
          <h2 className="text-lg font-medium text-gray-900">Recent Receipts</h2>
          <Link
            to="/upload"
            className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-indigo-600 hover:bg-indigo-700"
          >
            Upload New
          </Link>
        </div>
        <div className="divide-y divide-gray-200">
          {receipts.length === 0 ? (
            <div className="px-4 py-8 text-center text-gray-500">
              No receipts yet. Upload your first receipt to get started!
            </div>
          ) : (
            receipts.map((receipt) => (
              <Link
                key={receipt.id}
                to={`/receipts/${receipt.id}`}
                className="block hover:bg-gray-50 px-4 py-4"
              >
                <div className="flex items-center justify-between">
                  <div className="flex-1">
                    <p className="text-sm font-medium text-indigo-600 truncate">
                      {receipt.vendor || 'Unknown Vendor'}
                    </p>
                    <p className="text-sm text-gray-500">
                      {receipt.date ? new Date(receipt.date).toLocaleDateString() : 'No date'}
                    </p>
                  </div>
                  <div className="ml-2 flex-shrink-0 flex items-center">
                    <span className="text-sm font-medium text-gray-900 mr-4">
                      {receipt.currency} {receipt.total_amount ? parseFloat(receipt.total_amount).toFixed(2) : '0.00'}
                    </span>
                    <span className={`px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${
                      receipt.processing_status === 'done' ? 'bg-green-100 text-green-800' :
                      receipt.processing_status === 'processing' ? 'bg-yellow-100 text-yellow-800' :
                      receipt.processing_status === 'error' ? 'bg-red-100 text-red-800' :
                      'bg-gray-100 text-gray-800'
                    }`}>
                      {receipt.processing_status}
                    </span>
                  </div>
                </div>
              </Link>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
