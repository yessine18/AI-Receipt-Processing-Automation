import React, { useState } from 'react';
import { useQuery } from 'react-query';
import { Link } from 'react-router-dom';
import { receiptAPI } from '../api/client';
import { MagnifyingGlassIcon } from '@heroicons/react/24/outline';

export default function ReceiptList() {
  const [page, setPage] = useState(1);
  const [filters, setFilters] = useState({
    status: '',
    vendor: '',
  });

  const { data, isLoading } = useQuery(
    ['receipts', page, filters],
    () => receiptAPI.list({ page, page_size: 20, ...filters })
  );

  const receipts = data?.data?.receipts || [];
  const totalPages = data?.data?.total_pages || 1;

  const handleFilterChange = (key, value) => {
    setFilters({ ...filters, [key]: value });
    setPage(1);
  };

  return (
    <div className="px-4 sm:px-0">
      <div className="sm:flex sm:items-center sm:justify-between mb-6">
        <h1 className="text-2xl font-semibold text-gray-900">Receipts</h1>
        <Link
          to="/upload"
          className="mt-4 sm:mt-0 inline-flex items-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700"
        >
          Upload New
        </Link>
      </div>

      {/* Filters */}
      <div className="bg-white shadow rounded-lg p-4 mb-6">
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Status
            </label>
            <select
              value={filters.status}
              onChange={(e) => handleFilterChange('status', e.target.value)}
              className="block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
            >
              <option value="">All</option>
              <option value="pending">Pending</option>
              <option value="processing">Processing</option>
              <option value="done">Done</option>
              <option value="error">Error</option>
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Vendor
            </label>
            <div className="relative">
              <input
                type="text"
                value={filters.vendor}
                onChange={(e) => handleFilterChange('vendor', e.target.value)}
                placeholder="Search vendor..."
                className="block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
              />
              <MagnifyingGlassIcon className="absolute right-3 top-2.5 h-5 w-5 text-gray-400" />
            </div>
          </div>
        </div>
      </div>

      {/* Receipt list */}
      <div className="bg-white shadow overflow-hidden sm:rounded-lg">
        {isLoading ? (
          <div className="px-4 py-8 text-center text-gray-500">Loading...</div>
        ) : receipts.length === 0 ? (
          <div className="px-4 py-8 text-center text-gray-500">
            No receipts found
          </div>
        ) : (
          <ul className="divide-y divide-gray-200">
            {receipts.map((receipt) => (
              <li key={receipt.id}>
                <Link to={`/receipts/${receipt.id}`} className="block hover:bg-gray-50">
                  <div className="px-4 py-4 sm:px-6">
                    <div className="flex items-center justify-between">
                      <div className="flex-1">
                        <p className="text-sm font-medium text-indigo-600 truncate">
                          {receipt.vendor || 'Unknown Vendor'}
                        </p>
                        <div className="mt-2 flex items-center text-sm text-gray-500">
                          <span>{receipt.date ? new Date(receipt.date).toLocaleDateString() : 'No date'}</span>
                          <span className="mx-2">•</span>
                          <span>{receipt.category || 'Uncategorized'}</span>
                        </div>
                      </div>
                      <div className="ml-2 flex-shrink-0 flex items-center">
                        <div className="text-right mr-4">
                          <p className="text-sm font-medium text-gray-900">
                            {receipt.currency} {receipt.total_amount ? parseFloat(receipt.total_amount).toFixed(2) : '0.00'}
                          </p>
                          <p className="text-xs text-gray-500">
                            {new Date(receipt.created_at).toLocaleDateString()}
                          </p>
                        </div>
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
                  </div>
                </Link>
              </li>
            ))}
          </ul>
        )}
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="bg-white px-4 py-3 flex items-center justify-between border-t border-gray-200 sm:px-6 mt-4 rounded-lg shadow">
          <div className="flex-1 flex justify-between sm:hidden">
            <button
              onClick={() => setPage(p => Math.max(1, p - 1))}
              disabled={page === 1}
              className="relative inline-flex items-center px-4 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 disabled:opacity-50"
            >
              Previous
            </button>
            <button
              onClick={() => setPage(p => Math.min(totalPages, p + 1))}
              disabled={page === totalPages}
              className="ml-3 relative inline-flex items-center px-4 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 disabled:opacity-50"
            >
              Next
            </button>
          </div>
          <div className="hidden sm:flex-1 sm:flex sm:items-center sm:justify-between">
            <div>
              <p className="text-sm text-gray-700">
                Page <span className="font-medium">{page}</span> of{' '}
                <span className="font-medium">{totalPages}</span>
              </p>
            </div>
            <div>
              <nav className="relative z-0 inline-flex rounded-md shadow-sm -space-x-px">
                <button
                  onClick={() => setPage(p => Math.max(1, p - 1))}
                  disabled={page === 1}
                  className="relative inline-flex items-center px-2 py-2 rounded-l-md border border-gray-300 bg-white text-sm font-medium text-gray-500 hover:bg-gray-50 disabled:opacity-50"
                >
                  Previous
                </button>
                <button
                  onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                  disabled={page === totalPages}
                  className="relative inline-flex items-center px-2 py-2 rounded-r-md border border-gray-300 bg-white text-sm font-medium text-gray-500 hover:bg-gray-50 disabled:opacity-50"
                >
                  Next
                </button>
              </nav>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
