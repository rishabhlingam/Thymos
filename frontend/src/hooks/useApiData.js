    import { useEffect, useState } from 'react'

/**
 * Fetches JSON from a given API path, refetching whenever the params
 * object changes. Centralizes the loading/error/data pattern that was
 * previously duplicated across SummaryTable, ResponderBoxplot, and
 * BaselineSubset.
 *
 * @param {string} path - API path, e.g. '/api/comparison'
 * @param {object} params - query params, will be converted with URLSearchParams
 * @returns {{ data: any, loading: boolean, error: string|null }}
 */
export function useApiData(path, params = {}) {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const paramsKey = JSON.stringify(params)

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setError(null)

    const query = new URLSearchParams(params)
    fetch(`${path}?${query}`)
      .then((res) => {
        if (!res.ok) {
          throw new Error(`Request failed with status ${res.status}`)
        }
        return res.json()
      })
      .then((json) => {
        if (!cancelled) {
          setData(json)
          setLoading(false)
        }
      })
      .catch((err) => {
        if (!cancelled) {
          setError(err.message)
          setLoading(false)
        }
      })

    return () => {
      cancelled = true
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [path, paramsKey])

  return { data, loading, error }
}