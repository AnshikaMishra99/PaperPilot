import { useOutletContext } from 'react-router-dom'

/**
 * Shared app state provided by the layout route: documents, chat messages,
 * explanation mode, and the refresh helpers.
 */
export function useApp() {
  return useOutletContext()
}
