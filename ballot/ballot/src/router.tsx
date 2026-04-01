import {RouterProvider, createHashRouter} from "react-router";
import Layout, { LayoutErrorBoundary } from "./Layout.tsx";
import {Dashboard} from "@/pages/Dashboard.tsx";
    

export default function Router() {
  return (
    <RouterProvider router={createHashRouter([
        {
            path: "/",
            element: <Layout />,
            errorElement: <LayoutErrorBoundary />,
            children: [
                {
                    index: true,
                    element: <Dashboard />
                },
                {
                    path: "*",
                    element: <LayoutErrorBoundary />
                }
            ]
        }
    ])} />

  );
}