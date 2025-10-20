import React, { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from 'react-query';
import { receiptAPI } from '../api/client';
import { 
  ArrowLeftIcon, 
  PencilIcon, 
  TrashIcon,
  ArrowPathIcon
} from '@heroicons/react/24/outline';

export default function ReceiptDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [editing, setEditing] = useState(false);
  const [formData, setFormData] = useState({});

  const { data, isLoading } = useQuery(['receipt', id], () => receiptAPI.get(id), {
    onSuccess: (response) => {
      setFormData(response.data);
    }
  });

  const updateMutation = useMutation(
    (updates) => receiptAPI.update(id, updates),
    {
      onSuccess: () => {
        queryClient.invalidateQueries(['receipt', id]);
        setEditing(false);
      }
    }
  );

  const deleteMutation = useMutation(() => receiptAPI.delete(id), {
    onSuccess: () => {
      navigate('/receipts');
    }
  });

  const reprocessMutation = useMutation(() => receiptAPI.reprocess(id), {
    onSuccess: () => {
      queryClient.invalidateQueries(['receipt', id]);
    }
  });

  const receipt = data?.data;

  if (isLoading) {
    return <div className="px-4 py-8 text-center">Loading...</div>;
  }

  if (!receipt) {
    return <div className="px-4 py-8 text-center">Receipt not found</div>;
  }

  const handleSave = () => {
    updateMutation.mutate({
      vendor: formData.vendor,
      date: formData.date,
      total_amount: parseFloat(formData.total_amount),
      tax_amount: parseFloat(formData.tax_amount),
      category: formData.category,
      notes: formData.notes
    });
  };

  return (
    <div className="px-4 sm:px-0">
      <button
        onClick={() => navigate('/receipts')}
        className="mb-4 inline-flex items-center text-sm text-gray-500 hover:text-gray-700"
      >
        <ArrowLeftIcon className="h-4 w-4 mr-1" />
        Back to receipts
      </button>

      <div className="bg-white shadow overflow-hidden sm:rounded-lg">
        <div className="px-4 py-5 sm:px-6 flex justify-between items-center">
          <div>
            <h3 className="text-lg leading-6 font-medium text-gray-900">
              Receipt Details
            </h3>
            <p className="mt-1 max-w-2xl text-sm text-gray-500">
              {receipt.vendor || 'Unknown Vendor'}
            </p>
          </div>
          <div className="flex space-x-2">
            {!editing && (
              <>
                <button
                  onClick={() => setEditing(true)}
                  className="inline-flex items-center px-3 py-2 border border-gray-300 shadow-sm text-sm leading-4 font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50"
                >
                  <PencilIcon className="h-4 w-4 mr-1" />
                  Edit
                </button>
                <button
                  onClick={() => reprocessMutation.mutate()}
                  disabled={reprocessMutation.isLoading}
                  className="inline-flex items-center px-3 py-2 border border-gray-300 shadow-sm text-sm leading-4 font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50"
                >
                  <ArrowPathIcon className="h-4 w-4 mr-1" />
                  Reprocess
                </button>
                <button
                  onClick={() => {
                    if (window.confirm('Are you sure you want to delete this receipt?')) {
                      deleteMutation.mutate();
                    }
                  }}
                  className="inline-flex items-center px-3 py-2 border border-red-300 shadow-sm text-sm leading-4 font-medium rounded-md text-red-700 bg-white hover:bg-red-50"
                >
                  <TrashIcon className="h-4 w-4 mr-1" />
                  Delete
                </button>
              </>
            )}
          </div>
        </div>

        <div className="border-t border-gray-200 px-4 py-5 sm:px-6">
          {/* Status badge */}
          <div className="mb-4">
            <span className={`px-3 py-1 inline-flex text-sm leading-5 font-semibold rounded-full ${
              receipt.processing_status === 'done' ? 'bg-green-100 text-green-800' :
              receipt.processing_status === 'processing' ? 'bg-yellow-100 text-yellow-800' :
              receipt.processing_status === 'error' ? 'bg-red-100 text-red-800' :
              'bg-gray-100 text-gray-800'
            }`}>
              {receipt.processing_status}
            </span>
          </div>

          <dl className="grid grid-cols-1 gap-x-4 gap-y-6 sm:grid-cols-2">
            <div>
              <dt className="text-sm font-medium text-gray-500">Vendor</dt>
              <dd className="mt-1 text-sm text-gray-900">
                {editing ? (
                  <input
                    type="text"
                    value={formData.vendor || ''}
                    onChange={(e) => setFormData({...formData, vendor: e.target.value})}
                    className="block w-full border-gray-300 rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
                  />
                ) : (
                  receipt.vendor || 'N/A'
                )}
              </dd>
            </div>

            <div>
              <dt className="text-sm font-medium text-gray-500">Date</dt>
              <dd className="mt-1 text-sm text-gray-900">
                {editing ? (
                  <input
                    type="date"
                    value={formData.date || ''}
                    onChange={(e) => setFormData({...formData, date: e.target.value})}
                    className="block w-full border-gray-300 rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
                  />
                ) : (
                  receipt.date ? new Date(receipt.date).toLocaleDateString() : 'N/A'
                )}
              </dd>
            </div>

            <div>
              <dt className="text-sm font-medium text-gray-500">Total Amount</dt>
              <dd className="mt-1 text-sm text-gray-900">
                {editing ? (
                  <input
                    type="number"
                    step="0.01"
                    value={formData.total_amount || ''}
                    onChange={(e) => setFormData({...formData, total_amount: e.target.value})}
                    className="block w-full border-gray-300 rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
                  />
                ) : (
                  `${receipt.currency} ${receipt.total_amount ? parseFloat(receipt.total_amount).toFixed(2) : '0.00'}`
                )}
              </dd>
            </div>

            <div>
              <dt className="text-sm font-medium text-gray-500">Tax Amount</dt>
              <dd className="mt-1 text-sm text-gray-900">
                {editing ? (
                  <input
                    type="number"
                    step="0.01"
                    value={formData.tax_amount || ''}
                    onChange={(e) => setFormData({...formData, tax_amount: e.target.value})}
                    className="block w-full border-gray-300 rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
                  />
                ) : (
                  `${receipt.currency} ${receipt.tax_amount ? parseFloat(receipt.tax_amount).toFixed(2) : '0.00'}`
                )}
              </dd>
            </div>

            <div>
              <dt className="text-sm font-medium text-gray-500">Category</dt>
              <dd className="mt-1 text-sm text-gray-900">
                {editing ? (
                  <input
                    type="text"
                    value={formData.category || ''}
                    onChange={(e) => setFormData({...formData, category: e.target.value})}
                    className="block w-full border-gray-300 rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
                  />
                ) : (
                  receipt.category || 'N/A'
                )}
              </dd>
            </div>

            <div>
              <dt className="text-sm font-medium text-gray-500">Payment Method</dt>
              <dd className="mt-1 text-sm text-gray-900">{receipt.payment_method || 'N/A'}</dd>
            </div>

            <div className="sm:col-span-2">
              <dt className="text-sm font-medium text-gray-500">Notes</dt>
              <dd className="mt-1 text-sm text-gray-900">
                {editing ? (
                  <textarea
                    rows="3"
                    value={formData.notes || ''}
                    onChange={(e) => setFormData({...formData, notes: e.target.value})}
                    className="block w-full border-gray-300 rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
                  />
                ) : (
                  receipt.notes || 'No notes'
                )}
              </dd>
            </div>

            {receipt.line_items && receipt.line_items.length > 0 && (
              <div className="sm:col-span-2">
                <dt className="text-sm font-medium text-gray-500 mb-2">Line Items</dt>
                <dd className="mt-1">
                  <table className="min-w-full divide-y divide-gray-200">
                    <thead className="bg-gray-50">
                      <tr>
                        <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Description</th>
                        <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Qty</th>
                        <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Price</th>
                        <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Total</th>
                      </tr>
                    </thead>
                    <tbody className="bg-white divide-y divide-gray-200">
                      {receipt.line_items.map((item, idx) => (
                        <tr key={idx}>
                          <td className="px-4 py-2 text-sm text-gray-900">{item.description}</td>
                          <td className="px-4 py-2 text-sm text-gray-900">{item.quantity}</td>
                          <td className="px-4 py-2 text-sm text-gray-900">{item.unit_price}</td>
                          <td className="px-4 py-2 text-sm text-gray-900">{item.total_price}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </dd>
              </div>
            )}
          </dl>

          {editing && (
            <div className="mt-6 flex justify-end space-x-3">
              <button
                onClick={() => {
                  setEditing(false);
                  setFormData(receipt);
                }}
                className="px-4 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-700 hover:bg-gray-50"
              >
                Cancel
              </button>
              <button
                onClick={handleSave}
                disabled={updateMutation.isLoading}
                className="px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700"
              >
                {updateMutation.isLoading ? 'Saving...' : 'Save'}
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
