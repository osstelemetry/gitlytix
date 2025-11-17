
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { motion } from "framer-motion";
import { Activity, CheckCircle2, Clock, GitPullRequest } from 'lucide-react'

interface ProjectOverviewProps {
    firstResponseTime: string;
    avgIssueResolution: string;
    prReviewTime: string;
    // prSuccessRate: string;
  }
  
  const ProjectOverview: React.FC<ProjectOverviewProps> = ({ firstResponseTime, avgIssueResolution, prReviewTime }) => {
    return(
    <Card className="bg-white shadow-md h-full">
        <CardHeader>
        <CardTitle className="text-2xl">Project Overview</CardTitle>
        <CardDescription>Key project statistics</CardDescription>
        </CardHeader>
        <CardContent>
        <div className="grid grid-cols-1 gap-4">
            <motion.div 
            className="flex items-center space-x-2 bg-gray-50 p-3 rounded-lg"
            whileHover={{ scale: 1.05 }}
            transition={{ type: "spring", stiffness: 400, damping: 10 }}
            >
            <Clock className="h-8 w-8 text-blue-600" />
            <div>
                <p className="text-sm font-medium text-gray-600">First Response Time</p>
                <p className="text-2xl font-bold text-gray-900">{firstResponseTime}</p>   
            </div>
            </motion.div>
            <motion.div 
            className="flex items-center space-x-2 bg-gray-50 p-3 rounded-lg"
            whileHover={{ scale: 1.05 }}
            transition={{ type: "spring", stiffness: 400, damping: 10 }}
            >
            <CheckCircle2 className="h-8 w-8 text-blue-600" />
            <div>
                <p className="text-sm font-medium text-gray-600">Avg. Issue Resolution</p>
                <p className="text-2xl font-bold text-gray-900">{avgIssueResolution}</p>
            </div>
            </motion.div>
            <motion.div 
            className="flex items-center space-x-2 bg-gray-50 p-3 rounded-lg"
            whileHover={{ scale: 1.05 }}
            transition={{ type: "spring", stiffness: 400, damping: 10 }}
            >
            <GitPullRequest className="h-8 w-12 text-blue-600" />
            <div>
                <p className="text-sm font-medium text-gray-600">PR Review Time</p>
                <p className="text-2xl font-bold text-gray-900">{prReviewTime}</p>
            </div>
            </motion.div>
            {/* <motion.div 
            className="flex items-center space-x-2 bg-gray-50 p-3 rounded-lg"
            whileHover={{ scale: 1.05 }}
            transition={{ type: "spring", stiffness: 400, damping: 10 }}
            >
            <Activity className="h-8 w-8 text-blue-600" />
            <div>
                <p className="text-sm font-medium text-gray-600">PR Success Rate</p>
                <p className="text-2xl font-bold text-gray-900">{prSuccessRate}</p>
            </div>
            </motion.div> */}
        </div>
        </CardContent>
    </Card>
    )
}

export default ProjectOverview;
