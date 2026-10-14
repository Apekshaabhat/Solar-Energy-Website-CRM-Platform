import { createContext, useCallback, useContext, useMemo, useState } from "react";

const DashboardDataContext = createContext(null);

const initialProfile = {
  customerName: "",
  location: "",
  propertyType: "Residential",
};

export function DashboardDataProvider({ children }) {
  const [refreshToken, setRefreshToken] = useState(0);
  const [lastChangedEntity, setLastChangedEntity] = useState(null);

  const notifyCrmChange = useCallback((entityType = "crm") => {
    setLastChangedEntity(entityType);
    setRefreshToken((prev) => prev + 1);
  }, []);

  const value = useMemo(
    () => ({
      refreshToken,
      notifyCrmChange,
      lastChangedEntity,
      // Backward compatibility stubs for legacy components
      setEntityList: () => {},
      upsertEntity: () => notifyCrmChange(),
      deleteEntity: () => notifyCrmChange(),
      syncSharedCommonFields: () => {},
      updateCommonProfile: () => {},
    }),
    [refreshToken, notifyCrmChange, lastChangedEntity]
  );

  return <DashboardDataContext.Provider value={value}>{children}</DashboardDataContext.Provider>;
}

export function useDashboardData() {
  const context = useContext(DashboardDataContext);

  if (!context) {
    throw new Error("useDashboardData must be used within a DashboardDataProvider");
  }

  return context;
}
