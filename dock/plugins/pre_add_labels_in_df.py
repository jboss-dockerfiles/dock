"""
Pre build plugin which adds labels to dockerfile. Labels has to be specified as dict:

{
    "name": "add_labels_in_dockerfile",
    "args": {
        "labels": {
            "label1": "value1",
            "label 2": "some value"
        }
    }
}

this will add turn this dockerfile:

```dockerfile
FROM fedora
CMD date
```

into this:

```dockerfile
FROM fedora
LABEL "label1"="value1" "label 2"="some value"
CMD date
```

If you want to use quotes within keys or values, you have to escape those yourself.
"""
from dock.plugin import PreBuildPlugin


class AddLabelsPlugin(PreBuildPlugin):
    key = "add_labels_in_dockerfile"

    def __init__(self, tasker, workflow, labels):
        """
        constructor

        :param tasker: DockerTasker instance
        :param workflow: DockerBuildWorkflow instance
        :param labels: dict, key value pairs to set as labels
        """
        # call parent constructor
        super(AddLabelsPlugin, self).__init__(tasker, workflow)
        if not isinstance(labels, dict):
            raise RuntimeError("labels have to be dict")
        self.labels = labels

    def run(self):
        """
        run the plugin
        """
        with open(self.workflow.builder.df_path, 'r') as fp:
            lines = fp.readlines()

        # FIXME: should we escape quotes?
        # correct syntax is:
        #   LABEL "key"="value" "key2"="value2"
        content = 'LABEL'
        for key, value in self.labels.items():
            label = '"%s"="%s"' % (key, value)
            self.log.info("setting label %s", label)
            content += " " + label

        # put it before last instruction
        lines.insert(-1, content + '\n')

        with open(self.workflow.builder.df_path, 'w') as fp:
            fp.writelines(lines)

        return content
