import type { InternalAxiosRequestConfig } from 'axios'
import { api, ApiError, toApiError } from '../services/apiClient'
import { session } from '../services/session'

describe('api client', () => {
  it('sends the token, the active organization and the language on every request', async () => {
    session.setAccessToken('token-123')
    session.setOrganizationId('org-abc')
    let captured: InternalAxiosRequestConfig | undefined
    await api.get('/people/', {
      adapter: async (config) => {
        captured = config
        return { data: {}, status: 200, statusText: 'OK', headers: {}, config }
      },
    })
    expect(captured!.headers.get('Authorization')).toBe('Bearer token-123')
    expect(captured!.headers.get('X-Organization-ID')).toBe('org-abc')
    expect(captured!.headers.get('Accept-Language')).toBe('en')
    expect(captured!.headers.get('X-Client-Type')).toBe('web')
  })

  it('turns the API error envelope into a typed error with field messages', async () => {
    session.setAccessToken(null)
    const error = await api
      .post('/people/', {}, {
        adapter: async (config) => {
          throw Object.assign(new Error('Bad Request'), {
            isAxiosError: true,
            config,
            response: {
              status: 400,
              config,
              headers: {},
              statusText: 'Bad Request',
              data: {
                error: { code: 'validation_error', message: 'Some fields are invalid.', details: { mobile: [{ code: 'invalid_mobile', message: 'Enter a valid mobile number.' }] } },
                request_id: 'req-1',
              },
            },
          })
        },
      })
      .catch((e: unknown) => e)
    expect(error).toBeInstanceOf(ApiError)
    expect((error as ApiError).fieldError('mobile')).toBe('Enter a valid mobile number.')
    expect((error as ApiError).requestId).toBe('req-1')
  })

  it('reports network failures clearly', () => {
    const error = toApiError(Object.assign(new Error('Network Error'), { isAxiosError: true }))
    expect(error.code).toBe('network_error')
  })

  it('flattens nested errors such as one line of a payment', () => {
    const body = {
      error: {
        code: 'validation_error',
        message: 'Some fields are invalid.',
        details: {
          lines: { '1': { amount: [{ code: 'invalid', message: 'Amount must be more than zero.' }] } },
          payer: [{ code: 'does_not_exist', message: 'Invalid pk.' }],
          items: [{}, { amount: [{ code: 'min_value', message: 'Too small.' }] }],
        },
      },
      request_id: 'req-2',
    }
    const error = toApiError(Object.assign(new Error('Bad Request'), { isAxiosError: true, response: { status: 400, data: body } }))
    expect(error.fieldError('lines.1.amount')).toBe('Amount must be more than zero.')
    expect(error.fieldError('payer')).toBe('Invalid pk.')
    expect(error.fieldError('items.1.amount')).toBe('Too small.')
  })
})
