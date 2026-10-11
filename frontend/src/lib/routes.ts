// Inside a vehicle every page lives under /v/<vehicle>/…; "/" is the overview across all vehicles.
// Only the G60 is active, so links use a fixed base for now; the [vehicle] segment keeps the URLs ready
// for more vehicles.
export const VEHICLE = "g60";
export const V = `/v/${VEHICLE}`;
