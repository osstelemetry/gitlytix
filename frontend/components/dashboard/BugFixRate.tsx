import { motion } from "framer-motion"
import { Bug } from "lucide-react"
import { Card, CardContent, CardHeader, CardTitle } from "../ui/card"

interface BugFixRateProps {
    bugFixRate: string;
}

const BugFixRate: React.FC<BugFixRateProps> = ({ bugFixRate }) => {
    return (
        <Card className="bg-white shadow-md">
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Bug Fix Rate</CardTitle>
                <Bug className="h-4 w-4 text-blue-600" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold text-gray-900">{bugFixRate}</div>
                <p className="text-xs text-gray-500">average time to resolve</p>
              </CardContent>
            </Card>
    )
}
export default BugFixRate;
